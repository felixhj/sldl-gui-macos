import Foundation

struct Song: Identifiable {
    let id = UUID()
    let title: String
    var status: String = "Pending"
}
