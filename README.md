# DG Gateway Pro — Windows Dashboard

**Onafhankelijk TeamSpeak Regio Netwerk Nederland.** Windows-viewer zonder geluid of PTT. **Los van de werkende Android-app** in [DMR-Gateway-Pro](https://github.com/michiel66/DMR-Gateway-Pro).

> **Belangrijk:** DG-100 t/m DG-111 zijn onze eigen regiolabels in TeamSpeak-nicknames, **geen officiële DMR-talkgroups of echte radio-repeaters**. De Nederlandkaart gebruikt virtuele regiomarkers. Een gebruiker met de naam `DG-103 Michiel` hoort bij Zuid-Holland, ongeacht zijn werkelijke locatie.

## Wat werkt in de nieuwe Windows-versie?

- **Normale TeamSpeak-verbinding zonder portofoonapp of ServerQuery-account.** Net als [TS-Heerlen-pc](https://github.com/michiel66/TS-Heerlen-pc) wordt de vastgepinde, werkende [WebSpeak3](https://github.com/WebSpeak3/webspeak3) TS3-protocolconnector gebruikt. De pc meldt zich aan bij `heerlen.mijnts3.nl` als `DashboardView/gebruikersnaam`.
- **Geen audio of PTT op Windows:** de dashboardcode opent **geen microfoon**, stuurt **geen spraak** en gebruikt **geen luidspreker**. De onderliggende protocolconnector verwerkt inkomende pakketten uitsluitend om de TeamSpeak-spreekstatus vast te stellen; audiobuffers worden niet doorgegeven aan het dashboard. De viewerclient staat op *input muted*.
- **Echte online namen, kanalen en spreekactiviteit:** met normale TS3-rechten worden gebruikers via de protocolclient gelezen. Er is **geen TeamSpeak 3-installatie** nodig. Als de server weigert of de benodigde rechten beperkt, verschijnt een duidelijke foutmelding.
- **Kanaalkeuze:** het dashboard kan zijn eigen `DashboardView/naam`-client naar een gekozen TeamSpeak-kanaal verplaatsen. Zonder extra rechten ziet de client alleen spreekactiviteit in zijn eigen kanaal.
- **Nieuw: serverbrede RX/TX-monitor:** naast de normale client probeert de Windows-app elke circa 2 seconden via TeamSpeak ServerQuery `clientlist -voice` de daadwerkelijke `client_flag_talking` van gebruikers in **alle toegankelijke TeamSpeak-kanalen** te lezen. Hiervoor is geen geluid of microfoon nodig. Als lezen zonder inlog niet mag, kun je in het dashboard optioneel poort en een beperkt ServerQuery-leesaccount opgeven. Bij succes krijgen alle gelijktijdige sprekers een groene regiomarker, ongeacht hun kanaal, en verschijnen in Last Heard.
- **Eerlijke monitoringstatus:** bovenaan wordt zichtbaar of serverbrede RX/TX werkt, of de server slechts een deel van de gebruikers vrijgeeft, of alleen het eigen kanaal gevolgd kan worden. Dit is afhankelijk van de rechten op de Heerlen-server. De app verzint geen serverbrede spreekstatus.
- **Nederlandkaart:** twaalf virtuele regio's DG-100 t/m DG-111, plus DG-999 Overige. DG-103 is Zuid-Holland. Realtime spreekactiviteit wordt groen; Last Heard wordt alleen opgebouwd uit werkelijk gedetecteerde spreekevents.
- **Fullscreen:** de donkere neon-/zilverstijl past zich automatisch aan de schermgrootte aan.
- **Voorbeeld:** een duidelijk gemarkeerde demonstratiemodus met fictieve gegevens om de uitstraling te bekijken.
- **ServerQuery (beheer):** is optioneel een zelfstandige monitoringmodus. Ook daar wordt `client_flag_talking` gebruikt wanneer de server die waarde aanbiedt; bij ontbrekende flags verschijnt een melding.
- **Met Android:** tijdelijke QR-code en zescijferige koppelcode worden voorbereid op Windows. De huidige Android-app 2.0.2 heeft hiervoor **nog geen verbindingsmodule**.

### Wat is er technisch overgenomen?

De huidige [TS-Heerlen-pc](https://github.com/michiel66/TS-Heerlen-pc) Windows-app bouwt de WebSpeak3-protocolconnector vanaf exact commit `c2b52b323d2ef10e388b2b600444a98390c5cc7a`. Dit dashboard gebruikt **dezelfde vastgepinde upstream-versie**. Alleen de audio-PCM-uitvoer wordt uitgeschakeld; verbinding, users, channels, talkers en kanaalwissel blijven beschikbaar. Dit project voert **geen PTTConnect-UI/audio** uit.

**Belangrijke grens:** de gewone TeamSpeak-client kan niet zelfstandig naar alle kanalen luisteren. De extra ServerQuery-uitlezing werkt alleen als de server de poort, `clientlist -voice`, en voldoende rechten beschikbaar stelt. Sommige beheerders beperken de zichtbaarheid per kanaal. Het is daarom niet mogelijk alle kanalen te garanderen zonder toestemming of ondersteuning van de serverbeheerder. De polling van circa 2 seconden kan ultrakorte PTT-uitzendingen missen; de duur in Last Heard is een benadering. De Windows-app speelt of registreert nog steeds geen audio.

## Download Windows .exe

Ga naar [GitHub Actions](https://github.com/michiel66/DG-Gateway-Pro-Dashboard/actions), kies een geslaagde run van **Build Windows Viewer** en download onder **Artifacts** het ZIP-pakket `DG-Gateway-Pro-Windows`. Daarin zit `DG-Gateway-Pro-Dashboard.exe`.

Op Windows 10 of 11 is de **Microsoft Edge WebView2 Runtime** nodig. Die is op de meeste recente Windows-installaties aanwezig; de app controleert dit niet zelfstandig. De gedownloade exe is een zelfgebouwde/testbuild, zonder vertrouwde Windows-codeondertekening. Windows SmartScreen kan daarom waarschuwen.

## Aan de slag

1. Pak de geslaagde Windows-EXE uit en start `DG-Gateway-Pro-Dashboard.exe`.
2. Het dashboard opent schermvullend. De voorbeeldmodus bevat uitsluitend herkenbare testgegevens.
3. Kies **TeamSpeak direct** en vul je naam in, bijvoorbeeld **Michiel**.
4. Klik **Verbinden zonder audio**. Je verschijnt op de TeamSpeak-server als `DashboardView/Michiel`. Er is geen ServerQuery-account nodig.
5. De Windows-app probeert automatisch **Serverbrede RX/TX** via ServerQuery, terwijl `DashboardView/Michiel` gewoon met TeamSpeak verbonden blijft.
6. Bovenaan zie je **Serverbrede RX/TX** wanneer de server toestemming geeft. Bijvoorbeeld: `DG-103 Ruud` in kanaal 7 én `DG-104 Marcel` in kanaal 8 laten twee verschillende regio's tegelijk groen oplichten. Ook verschijnen de namen in Last Heard wanneer het zenden stopt.
7. Zie je **Alleen eigen kanaal**? Klik **RX/TX alle kanalen ⚙**. Controleer ServerQuery-poort (meestal 10011) en, indien nodig, vul gegevens in van een beperkt **alleen-lezen** ServerQuery-account dat de serverbeheerder voor je heeft toegestaan.
8. Het gewone TS-kanaal kun je bovenaan nog steeds kiezen, maar dit is niet nodig om van kanaal te wisselen wanneer serverbrede monitoring lukt. Je pc hoort niets en kan niet praten.
9. Als de melding **Gedeeltelijke RX/TX** verschijnt, kan het ServerQuery-account minder gebruikers zien dan de gewone TeamSpeak-client. Vraag de beheerder om voldoende leesrechten; toon alleen werkelijk beschikbare spreekstatus.
10. Via **Met Android** zie je de toekomstige QR-koppeling. Hiervoor is later een Android-update vereist.

## Windows-beveiliging en privacy

De Windows viewer slaat de door WebSpeak3 uitgegeven TeamSpeak-identiteit lokaal op in het gebruikersprofiel, zodat de server dezelfde bezoeker kan herkennen. De connector heeft geen toegang tot de microfoon, het dashboard speelt geen spraakgeluid af en maakt geen audio-opname. Alleen het connectorproces ontvangt protocolaudiopakketten voor spreekstatus. Wachtwoorden of serverbeheergegevens zijn niet vereist voor **TeamSpeak direct**. Gebruik je serverbrede RX/TX-uitlezing of de ServerQuery-beheermodus, geef dan uitsluitend beperkte leesrechten. De standaard TeamSpeak ServerQuery-poort 10011 is niet TLS-versleuteld; vul nooit een beheerderswachtwoord in op een onbeveiligd netwerk. Login en wachtwoord worden alleen tijdens de actuele softwaresessie in het werkgeheugen gebruikt, niet op schijf bewaard.

## Architectuur

- `app.py`: lokale API, echte TeamSpeak-gebruikers en RX-status, automatische serverbrede `clientlist -voice`-polling met eerlijke kanaaldekking en optionele leesrechten, beveiligde LAN-ontvanger en Windows-start.
- `direct_client.py`: start de vastgepinde normale WebSpeak3 TS3-connector als gedempte Windows-kijkclient; verwerkt uitsluitend users, channels en talkers.
- `scripts/patch_webspeak_viewer.py`: blokkeert PCM-uitvoer vanuit WebSpeak3 zonder de sprekersdetectie uit te schakelen.
- `ui/index.html`, `ui/style.css`, `ui/app.js`: responsief Nederland-dashboard met schematische provinciecontouren, geen externe CDNs of tracking.
- `.github/workflows/windows.yml`: Windows 64-bit PyInstaller testbuild, met de officiële WebSpeak3-connector ingebouwd.
- `tests/test_core.py`: regressietests voor DG-indeling, ServerQuery-escaping, spreekstatusverwerking en API-output.

Het project gebruikt Python, [pywebview](https://pywebview.flowrl.com/), cryptography, qrcode en de MIT-gelicentieerde [WebSpeak3](https://github.com/WebSpeak3/webspeak3)-connector. De originele WebSpeak3-LICENSE wordt met de Windows-EXE meegeleverd. Het dashboard wordt **uitsluitend lokaal** weergegeven; de lokale LAN-koppeling vereist een autorisatiecode en een door Android te verifiëren TLS-vingerafdruk. Gebruik de app alleen op vertrouwde netwerken.

## Privacy en rechten

Online namen en TG-/DG-prefixen zijn alleen beschikbaar volgens de toegangsrechten van de TeamSpeak-server. Het dashboard vraagt geen microfoonmachtiging en registreert geen audio-opnames. Het Last Heard-overzicht bevat uitsluitend namen, tijdstippen en spreekduur. Het schrijft geen gegevens terug naar de TeamSpeak-server. Maak geen ServerQuery-beheerdersaccount speciaal voor eindgebruikers; laat de beheerder een beperkt leesaccount maken.

*DG Gateway Pro is onafhankelijk van TeamSpeak Systems, DMR en BrandMeister.*
