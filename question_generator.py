from nltk.corpus import wordnet as wn
from textblob import TextBlob
import random
import re


class Article:
    def __init__(self, article):
        self.article = TextBlob(article)

    def generate_trivia_sentences(self):
        sentences = self.article.sentences
        trivia_sentences = []
        for sentence in sentences:
            trivia = self.evaluate_sentence(sentence)
            if trivia:
                trivia_sentences.append(trivia)

        return trivia_sentences

    def get_similar_words(self, word):
        synsets = wn.synsets(word, pos='n')
        if len(synsets) == 0:
            return []
        else:
            synset = synsets[0]
        hypernym = synset.hypernyms()[0]
        hyponyms = hypernym.hyponyms()
        similar_words = []
        for hyponym in hyponyms:
            similar_word = hyponym.lemmas()[0].name().replace('_', ' ')

            if similar_word != word:
                similar_words.append(similar_word)

            if len(similar_words) == 8:
                break

        return similar_words

    def evaluate_sentence(self, sentence):
        replace_nouns = []
        for s in sentence.tags:
            word, tag = s[0], s[1]
            if tag == 'NN':
                for phrase in sentence.noun_phrases:
                    if phrase[0] == '\'':
                        break

                    if word in phrase:
                        [
                            replace_nouns.append(phrase_word)
                            for phrase_word in phrase.split()[-2:]
                        ]
                        break
                if len(replace_nouns) == 0:
                    replace_nouns.append(word)
                break

        if len(replace_nouns) == 0:
            return None

        trivia = {
            "sentence": str(sentence),
        }
        trivia["answers"] = []
        correct_answer = ' '.join(replace_nouns)
        if len(replace_nouns) == 1:
            trivia['answers'].append(correct_answer)
            trivia['answers'].extend(
                self.get_similar_words(replace_nouns[0])[:3])
        random.shuffle(trivia['answers'])
        if len(trivia['answers']) < 3:
            return None
        if len(trivia['answers']) > 1:
            trivia['correctIndex'] = trivia['answers'].index(correct_answer)
            trivia['jumpToTime'] = 0

        if len(trivia['answers']) == 3:
            trivia['answers'].append('None of the Above')

        replace_phrase = correct_answer
        blanks_phrase = ('____ ' * len(replace_nouns)).strip()

        expression = re.compile(re.escape(replace_phrase), re.IGNORECASE)
        sentence = expression.sub(blanks_phrase, str(sentence), count=1)

        trivia["question"] = sentence
        return trivia


def generate_trivia(article):
    questions = []
    article = Article(article)
    generated_sentence = article.generate_trivia_sentences()
    if (generated_sentence):
        questions = questions + generated_sentence
    return questions
