# Gmail OAuth – nästa steg

## Plan

Nästa steg:

1. Skapa OAuth Desktop Client i Google Cloud + aktivera Gmail API.
2. Lägg client JSON som `gmail_credentials.json` i projektroten.
3. Kör:
   - `python -m pip install -r requirements.txt`
   - `python gmail_reader.py list --max-results 10`
4. Vid första körning: logga in i webbläsaren och ge read-only access.

## Hjälp med steg 1

Gör exakt detta i Google Cloud:

1. Öppna projekt
   - Gå till <https://console.cloud.google.com/>
   - Välj eller skapa ett projekt uppe i toppmenyn.

2. Aktivera Gmail API
   - Gå till **APIs & Services → Library**
   - Sök **Gmail API**
   - Klicka **Enable**

3. Konfigurera OAuth consent (Google Auth Platform)
   - Gå till **Google Auth Platform → Branding**
   - Klicka **Get started** (om första gången)
   - Fyll i appnamn + supportmail + kontaktmail
   - Slutför och skapa

4. Sätt Audience/Test users
   - Gå till **Google Auth Platform → Audience**
   - Välj **External** (för privat konto är detta vanligast)
   - Låt appen vara i **Testing**
   - Lägg till din egen Gmail under **Test users**

5. Skapa OAuth-klient (Desktop)
   - Gå till **Google Auth Platform → Clients**
   - **Create client**
   - **Application type = Desktop app**
   - Ge namn, klicka **Create**
   - Ladda ner JSON

6. Lägg filen i projektet
   - Spara den som `gmail_credentials.json` i:
     `/home/peter/Projekt/cdb-extraction`

När detta är klart, skriv **klart** så guidar jag dig i nästa kommando:
`python gmail_reader.py list --max-results 10`.
