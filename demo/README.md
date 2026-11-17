# DG Gateway Pro — blauwe kaart DEMO

**Dit is alleen een visuele demo; er wordt NIET met TeamSpeak verbonden.**

- De kaart met het lege linkervak is een zelfstandige achtergrondafbeelding; de programmaonderdelen zijn afzonderlijke HTML/CSS-overlays.
- 12 DG-regio's zoals in de werkende Android-app: DG-100 Noord-Holland, 101 Utrecht, 102 Zeeland, 103 Zuid-Holland, 104 Noord-Brabant, 105 Limburg, 106 Gelderland, 107 Overijssel, 108 Drenthe, 109 Groningen, 110 Friesland, 111 Flevoland.
- Bewegende fictieve RX/TX-balkjes, groene pulsringen, deelnemers per regio, Last Heard en lokale klok.
- Knoppen: Demo starten/pauzeren, volgende spreker, indeling aanpassen, posities herstellen.
- Markers en de twee losse zwevende panelen zijn met de muis te verslepen na **Indeling aanpassen**; posities worden alleen lokaal in browseropslag opgeslagen.
- Geen PTT, geen microfoon, geen echte TeamSpeak-servertoegang en geen audio.
- De demonstratiewaarden en -namen zijn **verzonnen en duidelijk gemarkeerd**.

## Download
Ga naar [Windows-demo builds](https://github.com/michiel66/DG-Gateway-Pro-Dashboard/actions/workflows/windows-demo.yml), kies een geslaagde **Bouw blauwe kaart demo (zonder TeamSpeak)**-run en download bij Artifacts `DG-Gateway-Pro-Blauwe-Kaart-Demo`.

In de ZIP zit zowel:
- `DG-Gateway-Pro-Blauwe-Kaart-Demo.exe`: standalone Windows-EXE met ingebouwde lokale browserweergave.
- `browser-demo/index.html`: dezelfde demo direct in de browser zonder installatie, ook offline.

**Over de achtergrond:** de demo gebruikt een compacte, sterk gecomprimeerde kopie van de eerder gekozen kaart (voor een lichte GitHub-preview). De originele afbeelding is 1536×1024 en blijft als ontwerpreferentie ongewijzigd. De overlay-positie werkt met percentages van het beeld, zodat losse onderdelen later gemakkelijk aanpasbaar zijn.

## Reservekopie TeamSpeak
De bestaande werkende TeamSpeak-code staat op de branch
[`backup-live-teamSpeak-2026-11-17`](https://github.com/michiel66/DG-Gateway-Pro-Dashboard/tree/backup-live-teamSpeak-2026-11-17).
De nieuwe demo is een **aparte Windows-startmodule** (`demo_launcher.py`) en laadt geen TeamSpeak-code; de huidige `app.py` blijft bestaan.
