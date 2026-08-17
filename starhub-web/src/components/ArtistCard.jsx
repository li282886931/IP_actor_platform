export default function ArtistCard({artist}){
  return (
    <div className="bg-white rounded-lg shadow p-4 text-black">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-purple-400 rounded-full flex items-center justify-center text-white">{artist.name && artist.name[0]}</div>
        <div>
          <div className="font-bold">{artist.name}</div>
          <div className="text-sm text-gray-500">{artist.tags}</div>
        </div>
      </div>
    </div>
  )
}
