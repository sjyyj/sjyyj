from __future__ import annotations
from time import time
from typing import TypedDict, Optional
from os import getenv
from unicodedata import normalize
from re import sub
import aiohttp

from dotenv import load_dotenv
from spacy import load

from sjyyj.openie import OpenIE5

load_dotenv()
extractor = OpenIE5('http://localhost:8000' if getenv('OPENIE_URL')
                    is None else getenv('OPENIE_URL'))


class Argument(TypedDict):
  text: str
  offsets: list[str]


class Extraction(TypedDict):
  arg1: Argument
  rel: Argument
  arg2s: list[Argument]
  context: None
  negated: bool
  passive: bool


class Triple(TypedDict):
  confidence: float
  # triple sentence has different value with tripled sentence because of ascii processing
  sentence: str
  extraction: Extraction
  score: float
  parent: TripledSentence


class TripledSentence(TypedDict):
  text: str
  triples: list[Triple]
  score: float


async def extract_triple(text: str, threshold=0.0) -> TripledSentence:
  sentence: TripledSentence = {'text': text, 'triples': [], 'score': 0}
  normalized = normalize('NFKD', text).encode(
      'ascii', 'ignore').decode('utf-8')
  try:
    async with aiohttp.ClientSession() as session:
      sentence['triples'] = await extractor.extract(normalized, session)
    filtered = []
    for triple in sentence['triples']:
      if triple['confidence'] >= threshold:
        filtered.append(triple)
    sentence['triples'] = filtered
  except Exception:
    sentence['triples'] = []
  for triple in sentence['triples']:
    triple['score'] = 0
    triple['parent'] = sentence
    tune_triple(triple)
  return sentence


def tune_triple(triple: Triple, pattern=r"\[|\]", repl=r"") -> None:
  extraction = triple['extraction']
  extraction['arg1']['text'] = sub(
      pattern, repl, extraction['arg1']['text'])
  extraction['rel']['text'] = sub(
      pattern, repl, extraction['rel']['text'])
  for arg2 in extraction['arg2s']:
    arg2['text'] = sub(pattern, repl, arg2['text'])


def triple2sentence(triple: Triple, arg2max: Optional[int] = None, glue: str = ' ', end: str = '') -> str:
  if arg2max is None:
    arg2max = len(triple['extraction']['arg2s'])
  return triple['extraction']['arg1']['text'] + glue + triple['extraction']['rel']['text'] + glue + \
      glue.join(
      list(map(lambda arg2: arg2['text'], triple['extraction']['arg2s']))[:arg2max]) + end


def doc2sentences(docstring: str, model="en_core_web_sm") -> list[str]:
  splitter = load(model)
  document = splitter(docstring)
  return [sent.text for sent in document.sents]


async def write_article(args: str) -> None:
  [d_i, document, path] = args.split('\n')
  start = time()
  sentences = doc2sentences(document)
  output = ''
  for s_i, sentence in enumerate(sentences):
    output += f'S\t{d_i}\t{s_i}\t{sentence}\n'
    triples = (await extract_triple(sentence))["triples"]
    for triple in triples:
      glue = '\t'
      output += f'R\t{triple2sentence(triple, None, glue)}\n'
    if len(triples) == 0:
      output += f'P\t{sentence}\n'
  with open(path, 'a', encoding='UTF8') as triplenote:
    triplenote.write(output)
  print(f'Article {int(d_i) + 1} Processed {(time() - start):.2f}sec')
