from gensim.summarization.summarizer import summarize

 
def get_summary(text):
    num_of_words = len(text.split())
    if num_of_words >= 5000:
        return (summarize(text,0.05))
    elif num_of_words >= 3000 and num_of_words < 5000 :
        return (summarize(text,0.1))
    elif num_of_words >= 1000 and num_of_words < 3000 :
        return (summarize(text,0.2))
    else:
        return (summarize(text,0.3))
