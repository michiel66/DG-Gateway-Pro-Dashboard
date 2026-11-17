# DG Gateway Pro — Windows Dashboard

**Onafhankelijk TeamSpeak Regio Netwerk Nederland.** Windows-viewer zonder geluid of PTT. **Los van de werkende Android-app** in [DMR-Gateway-Pro](https://github.com/michiel66/DMR-Gateway-Pro).

> **Belangrijk:** DG-100 t/m DG-111 zijn onze eigen regiolabels in TeamSpeak-nicknames, **geen officiële DMR-talkgroups of echte radio-repeaters**. De Nederlandkaart gebruikt virtuele regiomarkers. Een gebruiker met de naam `DG-103 Michiel` hoort bij Zuid-Holland, ongeacht zijn werkelijke locatie.

## Wat werkt in de nieuwe Windows-versie?

- **Normale TeamSpeak-verbinding zonder portofoonapp of ServerQuery-account.** Net als [TS-Heerlen-pc](https://github.com/michiel66/TS-Heerlen-pc) wordt de vastgepinde, werkende [WebSpeak3](https://github.com/WebSpeak3/webspeak3) TS3-protocolconnector gebruikt. De pc meldt zich aan bij `heerlen.mijnts3.nl` als `DashboardView/gebruikersnaam`.
- **Geen audio of PTT op Windows:** de dashboardcode opent **geen microfoon**, stuurt **geen spraak** en gebruikt **geen luidspreker**. De onderliggende protocolconnector verwerkt inkomende pakketten uitsluitend om de TeamSpeak-spreekstatus vast te stellen; audiobuffers worden niet doorgegeven aan het dashboard. De viewerclient staat op *input muted*.
- **Echte online namen, kanalen en spreekactiviteit:** met normale TS3-rechten worden gebruikers via de protocolclient gelezen. Er is **geen TeamSpeak 3-installatie** nodig. Als de server weigert of de benodigde rechten beperkt, verschijnt een duidelijke foutmelding.
- **Kanaalkeuze:** het dashboard kan zijn eigen `DashboardView/naam`-client naar een gekozen TeamSpeak-kanaal verplaatsen. Alleen de spreekactiviteit die de client kan waarnemen, doorgaans het eigen kanaal, activeert de groene regiomarkers.
- **Nederlandkaart:** twaalf virtuele regio's DG-100 t/m DG-111, plus DG-999 Overige. DG-103 is Zuid-Holland. Realtime spreekactiviteit wordt groen; Last Heard wordt alleen opgebouwd uit werkelijk gedetecteerde spreekevents.
- **Fullscreen:** de donkere neon-/zilverstijl past zich automatisch aan de schermgrootte aan.
- **Voorbeeld:** een duidelijk gemarkeerde demonstratiemodus met fictieve gegevens om de uitstraling te bekijken.
- **ServerQuery (beheer):** blijft als optionele aanvullende modus behouden; daarvoor zijn ServerQuery-rechten nodig en is geen spreekstatus beschikbaar.
- **Met Android:** tijdelijke QR-code en zescijferige koppelcode worden voorbereid op Windows. De huidige Android-app 2.0.2 heeft hiervoor **nog geen verbindingsmodule**.

### Wat is er technisch overgenomen?

De huidige [TS-Heerlen-pc](https://github.com/michiel66/TS-Heerlen-pc) Windows-app bouwt de WebSpeak3-protocolconnector vanaf exact commit `c2b52b323d2ef10e388b2b600444a98390c5cc7a`. Dit dashboard gebruikt **dezelfde vastgepinde upstream-versie**. Alleen de audio-PCM-uitvoer wordt uitgeschakeld; verbinding, users, channels, talkers en kanaalwissel blijven beschikbaar. Dit project voert **geen PTTConnect-UI/audio** uit.

Er zijn technische grenzen: sommige TeamSpeak-servers laten een gewone client niet alle kanalen zien of verbieden channel moves. Een gebruiker buiten het gekozen kanaal kan zichtbaar zijn zonder dat diens spreekstatus waarneembaar is. We beweren daarom niet alle kanalen gelijktijdig te monitoren.

## Download Windows .exe

Ga naar [GitHub Actions](https://github.com/michiel66/DG-Gateway-Pro-Dashboard/actions), kies een geslaagde run van **Build Windows Viewer** en download onder **Artifacts** het ZIP-pakket `DG-Gateway-Pro-Windows`. Daarin zit `DG-Gateway-Pro-Dashboard.exe`.

Op Windows 10 of 11 is de **Microsoft Edge WebView2 Runtime** nodig. Die is op de meeste recente Windows-installaties aanwezig; de app controleert dit niet zelfstandig. De gedownloade exe is een zelfgebouwde/testbuild, zonder vertrouwde Windows-codeondertekening. Windows SmartScreen kan daarom waarschuwen.

## Aan de slag

1. Pak de geslaagde Windows-EXE uit en start `DG-Gateway-Pro-Dashboard.exe`.
2. Het dashboard opent schermvullend. De voorbeeldmodus bevat uitsluitend herkenbare testgegevens.
3. Kies **TeamSpeak direct** en vul je naam in, bijvoorbeeld **Michiel**.
4. Klik **Verbinden zonder audio**. Je verschijnt op de TeamSpeak-server als `DashboardView/Michiel`. Er is geen ServerQuery-account nodig.
5. Zodra de echte kanalen verschijnen, kies bovenaan het kanaal dat je wilt observeren. Je pc hoort niets en kan niet praten.
6. Wanneer bijvoorbeeld `DG-103 Ruud` binnen het waargenomen kanaal spreekt, wordt het virtuele repeaterlogo van Zuid-Holland groen en wordt zijn gesprek geregistreerd in Last Heard.
7. Via **ServerQuery (beheer)** kan de serverbeheerder optioneel de oude queryuitlezing gebruiken, maar zonder spreekstatus.
8. Via **Met Android** zie je de toekomstige QR-koppeling. Hiervoor is later een Android-update vereist.

## Windows-beveiliging en privacy

De Windows viewer slaat de door WebSpeak3 uitgegeven TeamSpeak-identiteit lokaal op in het gebruikersprofiel, zodat de server dezelfde bezoeker kan herkennen. De connector heeft geen toegang tot de microfoon, het dashboard speelt geen spraakgeluid af en maakt geen audio-opname. Alleen het connectorproces ontvangt protocolaudiopakketten voor spreekstatus. Wachtwoorden of serverbeheergegevens zijn niet vereist voor **TeamSpeak direct**. Gebruik je de optionele ServerQuery-beheermodus, geef dan uitsluitend beperkte leesrechten.

## Architectuur

- `app.py`: lokale API, echte TeamSpeak-gebruikers en RX-status, optionele ServerQuery-polling, beveiligde LAN-ontvanger en Windows-start.
- `direct_client.py`: start de vastgepinde normale WebSpeak3 TS3-connector als gedempte Windows-kijkclient; verwerkt uitsluitend users, channels en talkers.
- `scripts/patch_webspeak_viewer.py`: blokkeert PCM-uitvoer vanuit WebSpeak3 zonder de sprekersdetectie uit te schakelen.
- `ui/index.html`, `ui/style.css`, `ui/app.js`: responsief Nederland-dashboard met schematische provinciecontouren, geen externe CDNs of tracking.
- `.github/workflows/windows.yml`: Windows 64-bit PyInstaller testbuild, met de officiële WebSpeak3-connector ingebouwd.
- `tests/test_core.py`: regressietests voor DG-indeling, ServerQuery-escaping, spreekstatusverwerking en API-output.

Het project gebruikt Python, [pywebview](https://pywebview.flowrl.com/), cryptography, qrcode en de MIT-gelicentieerde [WebSpeak3](https://github.com/WebSpeak3/webspeak3)-connector. De originele WebSpeak3-LICENSE wordt met de Windows-EXE meegeleverd. Het dashboard wordt **uitsluitend lokaal** weergegeven; de lokale LAN-koppeling vereist een autorisatiecode en een door Android te verifiëren TLS-vingerafdruk. Gebruik de app alleen op vertrouwde netwerken.

## Privacy en rechten

Online namen en TG-/DG-prefixen zijn alleen beschikbaar volgens de toegangsrechten van de TeamSpeak-server. Het dashboard vraagt geen microfoonmachtiging en registreert geen audio-opnames. Het Last Heard-overzicht bevat uitsluitend namen, tijdstippen en spreekduur. Het schrijft geen gegevens terug naar de TeamSpeak-server. Maak geen ServerQuery-beheerdersaccount speciaal voor eindgebruikers; laat de beheerder een beperkt leesaccount maken.

*DG Gateway Pro is onafhankelijk van TeamSpeak Systems, DMR en BrandMeister.*
