import Foundation

class TitleCleaner {
    func clean(title: String) -> String {
        var cleanedTitle = title
        // Remove text in parentheses and brackets
        cleanedTitle = cleanedTitle.replacingOccurrences(of: "\\s*\\([^)]*\\)", with: "", options: .regularExpression)
        cleanedTitle = cleanedTitle.replacingOccurrences(of: "\\s*\\[[^]]*\\]", with: "", options: .regularExpression)
        // Remove common keywords
        let keywords = ["official video", "official music video", "lyrics", "lyric video", "hd", "hq"]
        for keyword in keywords {
            cleanedTitle = cleanedTitle.replacingOccurrences(of: keyword, with: "", options: .caseInsensitive)
        }
        // Trim whitespace
        cleanedTitle = cleanedTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        return cleanedTitle
    }
}
