# DG Gateway Pro — Windows Dashboard

**Onafhankelijk TeamSpeak Regio Netwerk Nederland.** Windows-viewer zonder geluid of PTT. **Los van de werkende Android-app** in [DMR-Gateway-Pro](https://github.com/michiel66/DMR-Gateway-Pro).

> **Belangrijk:** DG-100 t/m DG-111 zijn onze eigen regiolabels in TeamSpeak-nicknames, **geen officiële DMR-talkgroups of echte radio-repeaters**. De Nederlandkaart gebruikt virtuele regiomarkers. Een gebruiker met de naam `DG-103 Michiel` hoort bij Zuid-Holland, ongeacht zijn werkelijke locatie.

## Wat werkt in deze eerste Windows-versie?

- Fullscreen Windows-app in de donkerblauwe/neonlook van het afgesproken ontwerp; responsieve Nederlandkaart, 12 DG-provincies + DG-999 Overige, live klok, keuze voor schermvullend venster.
- **Voorbeeldmodus:** herkenbare demonstratie met duidelijk het label **VOORBEELD**. Getoonde gebruikers, beweging en Last Heard zijn uitsluitend fictieve testgegevens.
- **Direct via TeamSpeak ServerQuery:** als de serverbeheerder **read-only ServerQuery-toegang** toestaat, kan het dashboard gebruikers en kanalen uitlezen, op kanaal filteren, en gebruikers op basis van hun DG-prefix per regio groeperen. Standaardserver: `heerlen.mijnts3.nl`. Query-poort standaard `10011`, TS3-voicepoort meestal `9987`. Querygegevens kunnen niet zonder toestemming van de serverbeheerder worden opgehaald.
- **Android-koppelontwerp:** bij starten krijgt Windows een nieuwe QR-code en een zescijferige code. Een lokale HTTPS-ontvanger met tijdelijke certificaatvingerafdruk staat klaar voor een **toekomstige update van de Android-app**. De Android-app 2.0.2 kan hiermee **nog niet koppelen**. Koppelcode verloopt en is bij herstart anders; geen automatische herverbinding.
- Geen audio-opname, geen RX/TX-geluid op Windows, geen PTT en geen microfoon.

### Wat werkt nog NIET zonder extra component?

De wens om zonder Android als een **normale** TeamSpeak-client genaamd `DashboardView/gebruikersnaam` te verbinden kan niet worden nagebootst met ServerQuery. Een queryverbinding is een *beheer-/leesinterface*, geen normale TeamSpeak 3-clientsessie, en maakt geen spraakverbinding. De standalone-modus in deze eerste versie is daarom expliciet **ServerQuery-viewer**, geen normale TeamSpeak-deelnemer. Voor een zichtbare normale TS-client is later een aparte protocolclient of officieel SDK-traject nodig.

ServerQuery kan online gebruikers en kanalen leveren, maar **geen betrouwbare realtime spreekactiviteit in alle kanalen**. Regiologo's worden in die modus daarom NIET fictief groen. Een `Last Heard`-overzicht verschijnt pas als daadwerkelijk spreekevents worden aangeleverd door een compatibele Android-upgrade/andere geautoriseerde bron.

## Download Windows .exe

Ga naar [GitHub Actions](https://github.com/michiel66/DG-Gateway-Pro-Dashboard/actions), kies een geslaagde run van **Build Windows Viewer** en download onder **Artifacts** het ZIP-pakket `DG-Gateway-Pro-Windows`. Daarin zit `DG-Gateway-Pro-Dashboard.exe`.

Op Windows 10 of 11 is de **Microsoft Edge WebView2 Runtime** nodig. Die is op de meeste recente Windows-installaties aanwezig; de app controleert dit niet zelfstandig. De gedownloade exe is een zelfgebouwde/testbuild, zonder vertrouwde Windows-codeondertekening. Windows SmartScreen kan daarom waarschuwen.

## Aan de slag

1. Pak het artifact-ZIP uit en start de Windows exe.
2. Het dashboard opent **schermvullend**. De **Voorbeeld**-modus is veilig om de indeling te bekijken.
3. Kies bovenaan **TeamSpeak direct** als je ServerQuery-toegang van de beheerder hebt. Vul je naam, host, querypoort, voicepoort en (indien vereist) ServerQuery-inloggegevens in. De Query-inloggegevens worden niet op de pc opgeslagen.
4. Bij een geslaagde verbinding worden gebruikers en kanalen ingelezen. Via **Kanaal** filter je de lijst. Afhankelijk van ServerQuery-rechten zijn sommige kanalen onzichtbaar.
5. De **Met Android**-modus toont QR en code plus de status **Android-update nodig**. Het is nu een veilige voorbereiding; de Android-app hoeft hiervoor niet aangepast te worden totdat we daar apart toestemming voor geven.
6. Druk op **Esc** of de fullscreenknop om de venstergrootte te wijzigen. De weergave past zich automatisch aan de grootte van het scherm aan.

## Architectuur

- `app.py`: lokale API, fictieve voorbeelddata, TeamSpeak ServerQuery-polling, beveiligde tijdelijke LAN-koppeling en Windows-start.
- `ui/index.html`, `ui/style.css`, `ui/app.js`: responsief Nederland-dashboard met schematische provinciecontouren, geen externe CDNs of tracking.
- `.github/workflows/windows.yml`: Windows 64-bit PyInstaller testbuild.
- `tests/test_core.py`: regressietests voor DG-indeling, ServerQuery-escaping, spreekstatusverwerking en API-output.

Het project gebruikt Python, [pywebview](https://pywebview.flowrl.com/), cryptography en qrcode. Het dashboard wordt **uitsluitend lokaal** weergegeven; de lokale LAN-koppeling vereist een autorisatiecode en een door Android te verifiëren TLS-vingerafdruk. Gebruik de app alleen op vertrouwde netwerken.

## Privacy en rechten

Online namen en TG-/DG-prefixen zijn alleen beschikbaar volgens de toegangsrechten van de TeamSpeak-server. Het dashboard vraagt geen microfoonmachtiging en registreert geen gesprekken. Het schrijft geen gegevens terug naar de TeamSpeak-server. Maak geen ServerQuery-beheerdersaccount speciaal voor eindgebruikers; laat de beheerder een beperkt leesaccount maken.

*DG Gateway Pro is onafhankelijk van TeamSpeak Systems, DMR en BrandMeister.*
