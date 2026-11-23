# Guest-text rulings: review records

The reports of the review rounds on `phase1/guest-text-rulings` (O69 to O72), kept verbatim apart from local paths,
which read `<scratchpad>`. The reviewers' probe scripts lived in that scratchpad and were not kept, so their
measurements are reproduced by the tests in `tests/test_text.py` or by rerunning the probe each report describes.

O71's cap was measured over the UDHR corpus (`github.com/eric-muller/udhr`, `data/udhr/*.xml`, 533 translations):
each file's text, tags stripped and NFC-normalised, was scanned for the longest run of characters in categories Mn
and Me.

O73's bound was counted by an automaton over four character classes (a visible letter, a mark, a character that
draws nothing, a joiner) that steps O61's joiner rule, O70's run and O71's stack; it was checked against
`player_text` on every class string up to length 8 (87,380 strings, no disagreement), then each class was weighted
by the most characters that pass in it at any position on Python 3.12 (1,729 marks, 19 inkless characters as kept
after NFC, 2 joiners). A lone mark counts as ink in the model, as in `player_text`. Delta 2 found the first weights
(1,698 marks, those NFC leaves alone after "a") too low.
