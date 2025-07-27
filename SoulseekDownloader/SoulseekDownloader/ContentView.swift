import SwiftUI

struct ContentView: View {
    @State private var playlistURL = ""
    @State private var songs: [Song] = []
    @State private var isDownloading = false
    private let youTube = YouTube()
    private let titleCleaner = TitleCleaner()
    private let soulseek = Soulseek()

    var body: some View {
        VStack {
            TextField("Enter YouTube Playlist URL", text: $playlistURL)
                .padding()
            Button("Download Songs") {
                isDownloading = true
                youTube.getPlaylistTitles(url: playlistURL) { titles in
                    if let titles = titles {
                        self.songs = titles.map { Song(title: titleCleaner.clean(title: $0)) }
                        for i in 0..<self.songs.count {
                            self.songs[i].status = "Downloading"
                            soulseek.download(song: self.songs[i].title)
                            self.songs[i].status = "Downloaded"
                        }
                    }
                    isDownloading = false
                }
            }
            .padding()
            .disabled(isDownloading)

            if isDownloading {
                ProgressView()
            }

            List(songs) { song in
                HStack {
                    Text(song.title)
                    Spacer()
                    Text(song.status)
                }
            }
        }
        .padding()
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
