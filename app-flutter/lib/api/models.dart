class MatchPublic {
  final String id;
  final String name;
  final String description;
  final double similarity;
  const MatchPublic({
    required this.id,
    required this.name,
    required this.description,
    required this.similarity,
  });

  factory MatchPublic.fromJson(Map<String, dynamic> json) => MatchPublic(
        id: json['id'] as String,
        name: json['name'] as String,
        description: json['description'] as String,
        similarity: (json['similarity'] as num).toDouble(),
      );
}

class RecognizeResponse {
  final MatchPublic? match;
  final String spoken;
  const RecognizeResponse({required this.match, required this.spoken});

  factory RecognizeResponse.fromJson(Map<String, dynamic> json) {
    final m = json['match'];
    return RecognizeResponse(
      match: m == null ? null : MatchPublic.fromJson(m as Map<String, dynamic>),
      spoken: json['spoken'] as String,
    );
  }
}
