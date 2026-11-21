import Taro from '@tarojs/taro'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  initiateOSSUpload: vi.fn(),
  completeOSSUpload: vi.fn(),
  readFile: vi.fn(),
  request: vi.fn(),
}))

vi.mock('@tarojs/taro', () => ({
  default: {
    getFileSystemManager: () => ({ readFile: mocks.readFile }),
    request: mocks.request,
  },
}))

vi.mock('./api', () => ({
  api: {
    initiateOSSUpload: mocks.initiateOSSUpload,
    completeOSSUpload: mocks.completeOSSUpload,
  },
}))

import { OSSUploadError, uploadEvidenceFile } from './ossUpload'

describe('uploadEvidenceFile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uploads bytes with signed headers before completing evidence creation', async () => {
    const calls: string[] = []
    const bytes = new ArrayBuffer(4)
    mocks.initiateOSSUpload.mockImplementation(async () => {
      calls.push('initiate')
      return {
        id: 7,
        provider: 'aliyun-oss',
        upload_url: 'https://bucket.oss-cn-hangzhou.aliyuncs.com/file.pdf?signature=real',
        method: 'PUT',
        headers: { 'Content-Type': 'application/pdf', 'x-oss-forbid-overwrite': 'true' },
      }
    })
    mocks.readFile.mockImplementation(({ success }) => {
      calls.push('read')
      success({ data: bytes })
    })
    mocks.request.mockImplementation(async (options) => {
      calls.push('put')
      expect(options).toMatchObject({
        url: 'https://bucket.oss-cn-hangzhou.aliyuncs.com/file.pdf?signature=real',
        method: 'PUT',
        data: bytes,
        header: {
          'Content-Type': 'application/pdf',
          'x-oss-forbid-overwrite': 'true',
        },
      })
      return { statusCode: 200 }
    })
    mocks.completeOSSUpload.mockImplementation(async () => {
      calls.push('complete')
      return { evidence: { id: 61 } }
    })

    const evidence = await uploadEvidenceFile({
      projectId: 42,
      file: { path: 'wxfile://contract.pdf', name: 'contract.pdf', size: 4 },
      evidenceName: '场馆合同',
    })

    expect(calls).toEqual(['initiate', 'read', 'put', 'complete'])
    expect(mocks.initiateOSSUpload).toHaveBeenCalledWith({
      project_id: 42,
      file_name: 'contract.pdf',
      content_type: 'application/pdf',
      evidence_type: 'document',
      source: '微信小程序',
      metadata: { name: '场馆合同' },
    })
    expect(mocks.completeOSSUpload).toHaveBeenCalledWith(7, { size: 4 })
    expect(evidence).toEqual({ id: 61 })
  })

  it.each([
    ['local-placeholder', '/oss/local-placeholder/file.pdf'],
    ['aliyun-oss', 'http://bucket.example.com/file.pdf?signature=bad'],
  ])('rejects unconfigured or non-HTTPS upload targets', async (provider, uploadUrl) => {
    mocks.initiateOSSUpload.mockResolvedValue({
      id: 7,
      provider,
      upload_url: uploadUrl,
      method: 'PUT',
      headers: {},
    })

    await expect(uploadEvidenceFile({
      projectId: 42,
      file: { path: 'wxfile://contract.pdf', name: 'contract.pdf', size: 4 },
      evidenceName: '',
    })).rejects.toEqual(expect.objectContaining<Partial<OSSUploadError>>({
      code: 'STORAGE_NOT_CONFIGURED',
    }))
    expect(Taro.request).not.toHaveBeenCalled()
    expect(mocks.completeOSSUpload).not.toHaveBeenCalled()
  })

  it('reports missing OSS credentials before reading the file', async () => {
    mocks.initiateOSSUpload.mockRejectedValue({ statusCode: 500 })

    await expect(uploadEvidenceFile({
      projectId: 42,
      file: { path: 'wxfile://contract.pdf', name: 'contract.pdf', size: 4 },
      evidenceName: '',
    })).rejects.toEqual(expect.objectContaining({
      code: 'STORAGE_NOT_CONFIGURED',
    }))
    expect(mocks.readFile).not.toHaveBeenCalled()
    expect(Taro.request).not.toHaveBeenCalled()
  })

  it('does not complete when OSS PUT fails', async () => {
    mocks.initiateOSSUpload.mockResolvedValue({
      id: 7,
      provider: 'aliyun-oss',
      upload_url: 'https://bucket.example.com/file.xlsx?signature=real',
      method: 'PUT',
      headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
    })
    mocks.readFile.mockImplementation(({ success }) => success({ data: new ArrayBuffer(8) }))
    mocks.request.mockResolvedValue({ statusCode: 403 })

    await expect(uploadEvidenceFile({
      projectId: 42,
      file: { path: 'wxfile://project.xlsx', name: 'project.xlsx', size: 8 },
      evidenceName: '',
    })).rejects.toEqual(expect.objectContaining({ code: 'OSS_PUT_FAILED' }))
    expect(mocks.completeOSSUpload).not.toHaveBeenCalled()
  })
})
