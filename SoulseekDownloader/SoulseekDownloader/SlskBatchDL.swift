import Foundation

class SlskBatchDL {
    func download(
        playlistURL: String,
        username: String,
        password: String,
        downloadPath: String,
        completion: @escaping (String) -> Void
    ) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/local/bin/sldl")

        var arguments = [
            playlistURL,
            "--user", username,
            "--pass", password
        ]

        if !downloadPath.isEmpty {
            arguments.append(contentsOf: ["--path", downloadPath])
        }

        process.arguments = arguments

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        pipe.fileHandleForReading.readabilityHandler = { pipe in
            if let line = String(data: pipe.availableData, encoding: .utf8) {
                DispatchQueue.main.async {
                    completion(line)
                }
            }
        }

        process.terminationHandler = { process in
            DispatchQueue.main.async {
                if process.terminationStatus == 0 {
                    completion("\n\nProcess terminated successfully.")
                } else {
                    completion("\n\nProcess terminated with an error.")
                }
            }
        }

        do {
            try process.run()
        } catch {
            completion("Error running sldl: \(error)")
        }
    }
}
