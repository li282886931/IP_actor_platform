import Taro from '@tarojs/taro'

import { api } from './api'

export interface SelectedMessageFile {
  path: string
  name: string
  size: number
  type?: string
}

interface UploadEvidenceFileOptions {
  projectId: number
  file: SelectedMessageFile
  evidenceName: string
}

const contentTypes: Record<string, string> = {
  csv: 'text/csv',
  doc: 'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  pdf: 'application/pdf',
  ppt: 'application/vnd.ms-powerpoint',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  txt: 'text/plain',
  xls: 'application/vnd.ms-excel',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

const contentTypeFor = (file: SelectedMessageFile) => {
  if (file.type?.includes('/')) return file.type
  const extension = file.name.split('.').pop()?.toLowerCase() || ''
  return contentTypes[extension] || 'application/octet-stream'
}

export class OSSUploadError extends Error {
  code: string

  constructor(code: string) {
    super(code)
    this.name = 'OSSUploadError'
    this.code = code
  }
}

const readFile = (filePath: string) => new Promise<ArrayBuffer>((resolve, reject) => {
  Taro.getFileSystemManager().readFile({
    filePath,
    success: ({ data }) => {
      if (data instanceof ArrayBuffer) resolve(data)
      else reject(new OSSUploadError('FILE_READ_FAILED'))
    },
    fail: reject,
  })
})

export async function uploadEvidenceFile({
  projectId,
  file,
  evidenceName,
}: UploadEvidenceFileOptions): Promise<Record<string, unknown>> {
  const contentType = contentTypeFor(file)
  let upload: Record<string, unknown>
  try {
    upload = await api.initiateOSSUpload({
      project_id: projectId,
      file_name: file.name,
      content_type: contentType,
      evidence_type: 'document',
      source: '微信小程序',
      metadata: { name: evidenceName },
    })
  } catch (error) {
    const statusCode = Number(
      error && typeof error === 'object' && 'statusCode' in error
        ? error.statusCode
        : 0,
    )
    if (statusCode === 500 || statusCode === 502) {
      throw new OSSUploadError('STORAGE_NOT_CONFIGURED')
    }
    throw error
  }
  const uploadId = Number(upload.id || 0)
  const provider = String(upload.provider || '')
  const uploadUrl = String(upload.upload_url || '')
  if (
    !uploadId
    || provider === 'local-placeholder'
    || !uploadUrl.startsWith('https://')
    || String(upload.method || '').toUpperCase() !== 'PUT'
  ) {
    throw new OSSUploadError('STORAGE_NOT_CONFIGURED')
  }

  const bytes = await readFile(file.path)
  const response = await Taro.request({
    url: uploadUrl,
    method: 'PUT',
    data: bytes,
    header: (upload.headers || {}) as Record<string, string>,
  })
  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw new OSSUploadError('OSS_PUT_FAILED')
  }

  const completed = await api.completeOSSUpload(uploadId, { size: file.size })
  const evidence = completed.evidence
  if (!evidence || typeof evidence !== 'object' || !Number((evidence as Record<string, unknown>).id || 0)) {
    throw new OSSUploadError('EVIDENCE_ID_MISSING')
  }
  return evidence as Record<string, unknown>
}
