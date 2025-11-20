from rich.console import Console
from rich.table import Table
from y2a.utils import get_spacy_document
from y2a.splitter import split_by_semantics

def show_tokens(doc):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Token")
    table.add_column("POS", style="green")
    table.add_column("Dep")
    table.add_column("Head")

    for token in doc:
        table.add_row(
            str(token.i),
            token.text,
            token.pos_,
            token.dep_,
            token.head.text,
        )

    console = Console()
    console.print(table)

def main():
    config = {
        "words_limit": 5,
    }
    # doc = get_spacy_document("But, you know, honestly though, I have to say, like, last time I always had the air conditioning on during the summer and I didn't get charged more than, you know, the usual rent.", config)

    doc = get_spacy_document("And when I talked to him, he was like, \"Oh, you're pretty cool. You should come to my house.\" now we're going to go play at his house, I guess. I just wanted to be sure that you were there with me when I went for the first time.", config)

    sentences = split_by_semantics(doc, config)
    
    for s in sentences:
        print(s)

    show_tokens(doc)

if __name__ == "__main__":
    main()