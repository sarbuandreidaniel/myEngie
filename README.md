# MyEngie România — Integrare Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/sarbuandreidaniel/ha-myEngie?style=flat-square&label=Versiune)](https://github.com/sarbuandreidaniel/ha-myEngie/releases)
[![HA Min Version](https://img.shields.io/badge/Home%20Assistant-%3E%3D2024.1.0-blue?style=flat-square)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/Licen%C8%9B%C4%83-MIT-green.svg?style=flat-square)](LICENSE)
[![Susține](https://img.shields.io/badge/Sus%C8%9Bine-Buy%20Me%20a%20Coffee-yellow?style=flat-square&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/sarbuandreidaniel)
[![Revolut](https://img.shields.io/badge/Sus%C8%9Bine--m%C4%83%20prin-Revolut-blue?style=flat-square&logo=revolut)](https://revolut.me/andreisarbu/pocket/BPJpX9dppQ)

O integrare profesională pentru Home Assistant care conectează contul tău **MyEngie România** direct la platforma de smart home. Monitorizează consumul de gaze, soldul contului, facturile și mult mai mult — totul dintr-un singur loc.

---

## Ce oferă integrarea

### Funcționalități disponibile
- **Autentificare securizată** — Login prin Auth0, același mecanism ca aplicația oficială MyEngie
- **Sold cont** — Soldul în timp real, exprimat în RON
- **Index gaze** — Indexul curent de consum (m³) și fereastra pentru citirea următoare
- **Facturi** — Istoricul complet pentru anul curent și cel precedent, ultima factură, plăți restante
- **Stare cont** — Vizualizare rapidă dacă contul este la zi sau are restanțe
- **Notificări** — Numărul de notificări necitite din contul ENGIE
- **Detalii consum** — Senzor agregat cu date despre instalație, cod POC/POD și altele

### În curând
- 📋 Suport pentru consum electric (când API-ul devine disponibil)
- 📋 Transmitere automată a indexului
- 📋 Grafice și statistici de consum
- 📋 Suport pentru mai multe instalații
- 📋 Alerte de plată prin notificări HA

---

## Instalare

### Prin HACS (Recomandat)

1. Asigură-te că [HACS](https://hacs.xyz/) este instalat
2. Mergi la **HACS → Integrări → ⋮ → Depozite personalizate**
3. Adaugă:
   - **URL:** `https://github.com/sarbuandreidaniel/ha-myEngie`
   - **Categorie:** Integration
4. Caută **MyEngie** și instalează
5. Repornește Home Assistant

### Instalare manuală

```bash
cp -r custom_components/myengie ~/.homeassistant/custom_components/
```

Apoi repornești Home Assistant.

---

## Configurare

1. Mergi la **Setări → Dispozitive și servicii → Integrări**
2. Apasă **Adaugă integrare** și caută **MyEngie**
3. Introdu datele de autentificare ENGIE România:
   - **Email** — adresa cu care ești înregistrat la ENGIE România
   - **Parolă** — parola contului tău MyEngie
4. Apasă **Trimite**

Integrarea se va autentifica, va prelua datele instalației tale și va crea automat toți senzorii.

---

## Senzori disponibili

| Senzor | Descriere | Unitate |
|--------|-----------|---------|
| `sensor.myengie_balance` | Soldul curent al contului | RON |
| `sensor.myengie_gas_index` | Indexul de consum gaze | m³ |
| `sensor.myengie_unread_notifications` | Notificări necitite | — |
| `sensor.myengie_consumption_details` | Senzor rezumat cu 9+ atribute | — |
| `sensor.myengie_account_status` | Stare cont: La zi / Restanțe | — |
| `sensor.myengie_invoice_count` | Număr total facturi | — |
| `sensor.myengie_pending_payments` | Total plăți restante | RON |
| `sensor.myengie_latest_invoice` | Ultima factură: sumă, dată, scadență | RON |
| `sensor.myengie_invoice_history_AAAA` | Istoricul facturilor pentru anul AAAA | — |

> Senzorii de istoric sunt generați automat pentru **anul curent** și **anul precedent**.

### Atribute senzori

**`sensor.myengie_gas_index`** include:
- `next_read_start` — Începutul ferestrei pentru citirea indexului
- `next_read_end` — Sfârșitul ferestrei pentru citirea indexului

**`sensor.myengie_consumption_details`** include:
- Index gaze, sold, număr notificări, număr facturi, plăți restante, stare cont, detalii instalație, coduri POC/POD și altele

**`sensor.myengie_invoice_history_AAAA`** include:
- Lista completă de facturi cu sumă, dată emisie, scadență, stare (plătită/restantă) și totaluri

---

## Automatizări și șabloane

Exemplu — alertă când apare o nouă factură neachitată:

```yaml
automation:
  - alias: "Factură ENGIE nouă în așteptare"
    trigger:
      - platform: numeric_state
        entity_id: sensor.myengie_pending_payments
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Factură ENGIE nouă"
          message: "Ai o plată în așteptare de {{ states('sensor.myengie_pending_payments') }} RON"
```

---

## Rezolvarea problemelor

| Problemă | Soluție |
|----------|---------|
| Date de autentificare invalide | Folosește adresa de email completă și aceeași parolă ca în aplicația MyEngie |
| Cont blocat | Prea multe încercări eșuate — așteaptă câteva minute |
| Fără date / senzori indisponibili | Verifică jurnalele HA și conexiunea la internet |
| Date vechi | Intervalul implicit de actualizare este 1 oră; repornește integrarea pentru o actualizare forțată |

### Script de depanare

Testează autentificarea independent de Home Assistant:

```bash
cd /path/to/ha-myEngie
python3 debug_auth.py
```

---

## Confidențialitate și securitate

- Datele de autentificare sunt stocate securizat prin sistemul de intrări de configurare al Home Assistant — niciodată în text simplu
- Autentificarea folosește Auth0 (OAuth2), același furnizor ca aplicația oficială MyEngie
- Se fac doar apelurile API strict necesare
- Nicio dată nu este trimisă către servicii terțe
- Conform GDPR — toate datele rămân local în instanța ta Home Assistant

---

## Dezvoltare

### Structura proiectului

```
custom_components/myengie/
├── __init__.py           # Configurare integrare și coordinator
├── api.py                # Client API MyEngie
├── auth.py               # Autentificare Auth0
├── config_flow.py        # Flux de configurare UI
├── const.py              # Constante
├── sensor.py             # Entități senzori
├── manifest.json         # Metadate integrare
└── translations/
    ├── en.json           # Traduceri engleze
    └── ro.json           # Traduceri române
```

### Contribuții

Pull request-urile sunt binevenite. Te rugăm să deschizi un issue înainte de modificări majore.

---

## Documentație

- [Referință rapidă](docs/QUICK_REFERENCE.md)
- [Detalii implementare](docs/IMPLEMENTATION.md)
- [Istoric facturi](docs/INVOICE_HISTORY.md)
- [Utilizare senzori facturi](docs/USING_INVOICE_SENSORS.md)
- [Referință API](docs/API_REFERENCE.md)
- [Ghid dezvoltare](docs/DEVELOPMENT.md)

---

## Susține proiectul

Dacă această integrare îți economisește timp și îți face casa mai inteligentă, poți susține dezvoltarea ei:

[![Susține cu o cafea](https://img.shields.io/badge/Cump%C4%83r%C4%83--mi%20o%20cafea-Sus%C8%9Bine%20proiectul-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/sarbuandreidaniel)

[![Susține-mă prin Revolut](https://img.shields.io/badge/Sus%C8%9Bine--m%C4%83%20prin-Revolut-blue?style=for-the-badge&logo=revolut)](https://revolut.me/andreisarbu/pocket/BPJpX9dppQ)

---

## Licență

Licențiat sub [MIT License](LICENSE).

---

> **Disclaimer:** Aceasta este o integrare neoficială, dezvoltată de comunitate. Nu este afiliată cu și nu este aprobată de ENGIE România. Folosești pe propria răspundere și respectând termenii și condițiile ENGIE.

---

**Autor:** [Andrei Sarbu](https://github.com/sarbuandreidaniel) · **Actualizat:** Aprilie 2026
