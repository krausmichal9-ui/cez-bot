# ČEZ Geoportál Bot 🤖

Webová aplikace pro automatické vyplnění žádosti o sdělení o existenci sítí.

---

## Jak nasadit na internet (krok za krokem)

### 1. Vytvoř si GitHub účet
Jdi na https://github.com a zaregistruj se.

### 2. Vytvoř nový repozitář
- Klikni na zelené tlačítko **New** (vlevo nahoře)
- Název: `cez-bot`
- Zvol **Public**
- Klikni **Create repository**

### 3. Nahraj soubory
Na stránce repozitáře klikni na **uploading an existing file**,
přetáhni všechny soubory z této složky a klikni **Commit changes**.

### 4. Nasaď na Railway
- Jdi na https://railway.app
- Přihlaš se přes GitHub (tlačítko **Login with GitHub**)
- Klikni **New Project** → **Deploy from GitHub repo**
- Vyber `cez-bot`
- Railway automaticky najde Procfile a nasadí appku

### 5. Získej URL
- V Railway projektu klikni na **Settings** → **Domains** → **Generate Domain**
- Dostaneš URL ve tvaru `cez-bot-xxx.railway.app`
- To je tvoje webová aplikace! Sdílej ji s kýmkoli

---

## Použití aplikace
1. Otevři URL v prohlížeči
2. Vyplň jméno, příjmení, e-mail a adresu
3. Klikni **Spustit robota**
4. Sleduj průběh v reálném čase
5. Na konci se zobrazí screenshot rekapitulace — otevři odkaz a ručně potvrď odeslání

---

## Poznámky
- Finální odeslání žádosti je záměrně ruční (souhlas s podmínkami)
- Aplikace neukládá žádné osobní údaje
