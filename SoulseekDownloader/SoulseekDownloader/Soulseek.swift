import Foundation

class Soulseek {
    func download(song: String) {
        let appleScript = """
        tell application "Soulseek"
            activate
            tell application "System Events"
                keystroke "s" using {command down}
                delay 1
                keystroke "\(song)"
                delay 1
                key code 36
                delay 2
                click at {100, 100} -- Adjust these coordinates to the location of the first result
                delay 1
                keystroke "d" using {command down}
            end tell
        end tell
        """

        var error: NSDictionary?
        if let scriptObject = NSAppleScript(source: appleScript) {
            if let output = scriptObject.executeAndReturnError(&error) {
                print(output.stringValue ?? "")
            } else if let error = error {
                print("Error executing AppleScript: \(error)")
            }
        }
    }
}
