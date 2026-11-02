# Lain typography

Font files supplied by the project owner from `D:/alves/study/lainfonts`.

| Bundled file | Family | Interface role from supplied guide |
|---|---|---|
| TrixiePlain.otf | Trixie-Plain | `aeon` wordmark; the guide's `lain` logo face |
| NarrowbandPrime.ttf | Narrowband Prime ICG | Lowercase page titles and navigation; the guide's `serial experiments` face |
| LoveLetterTypewriter.ttf | Love Letter Typewriter | Section headings; the guide's Layer screens |
| ChiantiRoman.ttf | Chianti BT Roman | Labels, descriptions and values; the guide's `make me...` text |
| RotisExtraBold.otf | Rotis Semi Sans Std 75 Extra Bold | Actions; the guide's `Close the world, Open the nExt` text |

The supplied Mom's Typewriter is reserved for the guide's `re:` use. No `re:` element exists in this panel, so that file is not bundled. `qml/Typography.qml` declares the actual family names; font sizes and weights are tuned for native controls. The earlier generated composition remains the layout reference; the user's font guide supersedes its typography.

The supplied LoveLetter omits `ã`, ellipsis and middle dot; its `ç` slot is ornamental. Section headings containing `ã` or `ç` use the supplied Trixie face for the entire heading. Qt's Latin/common fallback is explicitly Chianti BT for other missing glyphs. Portuguese wording and diacritics are preserved. All five bundled families are registered from resources and remain available without installing them in Windows.
