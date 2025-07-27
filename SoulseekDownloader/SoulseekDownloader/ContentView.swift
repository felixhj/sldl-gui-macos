import SwiftUI

struct ContentView: View {
    @State private var playlistURL = ""
    @State private var username = ""
    @State private var password = ""
    @State private var downloadPath = ""
    @State private var outputText = ""
    private let slskBatchDL = SlskBatchDL()

    var body: some View {
        VStack {
            TextField("Enter YouTube Playlist URL", text: $playlistURL)
                .padding()
            TextField("Soulseek Username", text: $username)
                .padding()
            SecureField("Soulseek Password", text: $password)
                .padding()
            TextField("Download Path", text: $downloadPath)
                .padding()
            Button("Download Songs") {
                outputText = ""
                slskBatchDL.download(
                    playlistURL: playlistURL,
                    username: username,
                    password: password,
                    downloadPath: downloadPath
                ) { output in
                    outputText += output
                }
            }
            .padding()
            ScrollView {
                Text(outputText)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding()
        }
        .padding()
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
