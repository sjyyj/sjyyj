from typing import Tuple

from src.extract import extract_triple, TripledSentence, doc2sentences, Triple
from src.abstract import abstract
from src.rank import rank


def summarize(text: str) -> Tuple[str, list[TripledSentence], list[Triple]]:
  # Extract Sentences & Triples
  tripled_sentences: list[TripledSentence] = []
  try:
    sentences = doc2sentences(text)
    for sentence in sentences:
      tripled_sentences.append(extract_triple(sentence))
  except Exception as e:
    print(e)
    return 'Cannot extract summary', [], []
  if len(tripled_sentences) == 0:
    return 'Cannot extract summary', [], []

  # Abstraction
  sentence_rank, triple_rank = rank(tripled_sentences)
  return abstract(triple_rank), sentence_rank, triple_rank
