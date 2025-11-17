from .utils import get_spacy_document
from rich.console import Console
from rich.table import Table

def test():
    config = {}
    # doc = get_spacy_document("And usually the on the balconies here they have like a a drop down emergency like fire ladders and stuff and they usually have to have like a staff go around and check everything.", config)
    # doc = get_spacy_document("They tested that the ladder was working and whatnot.", config)
    doc = get_spacy_document("But, you know, honestly though, I have to say, like, last time I always had the air conditioning on during the summer and I didn't get charged more than, you know, the usual rent.", config)

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