# Appunti pubblici

Un sito personale, statico e senza fronzoli: ogni giorno un contenuto (testo, foto o video) che ha in qualche modo alimentato il lato destro del mio cervello. Nessun CMS, nessun framework, nessun tracciamento.

**Sito**: https://mariogaio.github.io/

## Come funziona

Un generatore Python legge i contenuti da `contenuti/*.md` (un file per contenuto, con data e tipo nel frontmatter) e produce pagine HTML statiche: una home a scorrimento in ordine cronologico inverso, più un link permanente per ogni contenuto. Nessuna dipendenza esterna, solo libreria standard di Python.

```
python script/build.py
```

Il sito è ospitato su GitHub Pages e si aggiorna a ogni push su `master`.

## Licenza e crediti

Il codice del generatore è libero da riprendere come ispirazione. I contenuti pubblicati restano di proprietà dei rispettivi autori quando non originali; ogni citazione riporta la fonte.
