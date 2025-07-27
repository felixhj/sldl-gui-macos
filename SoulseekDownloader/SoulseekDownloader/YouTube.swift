import Foundation

class YouTube {
    func getPlaylistTitles(url: String, completion: @escaping ([String]?) -> Void) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/local/bin/youtube-dl")
        process.arguments = ["--get-title", url]

        let pipe = Pipe()
        process.standardOutput = pipe

        process.terminationHandler = { process in
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8)
            let titles = output?.components(separatedBy: .newlines).filter { !$0.isEmpty }
            completion(titles)
        }

        do {
            try process.run()
        } catch {
            print("Error running youtube-dl: \\(error)")
            completion(nil)
        }
    }
}
