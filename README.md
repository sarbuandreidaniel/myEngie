# MyEngie România — Integrare Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/sarbuandreidaniel/myEngie?style=flat-square&label=Versiune)](https://github.com/sarbuandreidaniel/myEngie/releases)
[![HA Min Version](https://img.shields.io/badge/Home%20Assistant-%3E%3D2024.1.0-blue?style=flat-square)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/Licen%C8%9B%C4%83-MIT-green.svg?style=flat-square)](LICENSE)
[![Susține](https://img.shields.io/badge/Sus%C8%9Bine-Buy%20Me%20a%20Coffee-yellow?style=flat-square&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/sarbuandreidaniel)
[![Revolut](https://img.shields.io/badge/Sus%C8%9Bine--m%C4%83%20prin-Revolut-blue?style=flat-square&logo=revolut)](https://revolut.me/andreisarbu/pocket/BPJpX9dppQ)

O integrare profesională pentru Home Assistant care conectează contul tău **MyEngie România** direct la platforma de smart home. Monitorizează consumul de gaze, soldul contului, facturile și mult mai mult — totul dintr-un singur loc.

---

## Ce oferă integrarea

### Funcționalități disponibile
- **Autentificare securizată** — Login prin Auth0, același mecanism ca aplicația oficială MyEngie
- **Sold și scadențe** — Soldul în timp real, data scadenței și zilele rămase până la scadență
- **Index gaze** — Indexul curent de consum (m³) și fereastra pentru citirea următoare
- **Trimitere index gaze** — Introdu și trimite indexul contorului direct din Home Assistant; disponibil doar în fereastra de autoîncasare
- **Identificatori instalație** — Cod POC, POD și numărul instalației pentru fiecare punct de consum
- **Facturi** — Ultima factură, suma neachitată, scadența, indicator restanță
- **Istoricul facturilor** — Totaluri anuale cu defalcare lunară pentru anul curent și cel precedent
- **Consum lunar** — Consumul din luna precedentă (m³) și media lunară pe 12 luni
- **Plăți restante** — Total și detalii plăți restante, inclusiv scadențele depășite

### În curând
- 📋 Suport pentru consum electric
- 📋 Grafice și statistici de consum
- 📋 Alerte de plată prin notificări HA

---

## Instalare

### Prin HACS (Recomandat)

1. Asigură-te că [HACS](https://hacs.xyz/) este instalat
2. Mergi la **HACS → Integrări → ⋮ → Depozite personalizate**
3. Adaugă:
   - **URL:** `https://github.com/sarbuandreidaniel/myEngie`
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

## Entități disponibile

Integrarea creează automat câte un set complet de entități pentru fiecare **punct de consum** (instalație) din contul tău.

### Senzori

| Senzor | Descriere | Unitate |
|--------|-----------|---------|
| `sensor.myengie_<loc>_balance` | Soldul curent al contului | RON |
| `sensor.myengie_<loc>_unpaid_invoice` | Suma facturii neachitate | RON |
| `sensor.myengie_<loc>_gas_index` | Indexul curent de consum gaze | m³ |
| `sensor.myengie_<loc>_poc_number` | Numărul punctului de consum (POC) | — |
| `sensor.myengie_<loc>_pod` | Codul punctului de livrare (POD) | — |
| `sensor.myengie_<loc>_installation_number` | Numărul instalației (contor) | — |
| `sensor.myengie_<loc>_last_month_m3` | Consumul din luna precedentă | m³ |
| `sensor.myengie_<loc>_consumption_history_AAAA` | Consum total gaze în anul AAAA | m³ |
| `sensor.myengie_<loc>_invoice_history_AAAA` | Total facturat în anul AAAA | RON |

### Trimitere index gaze

| Entitate | Descriere | Disponibilitate |
|----------|-----------|-----------------|
| `number.myengie_<loc>_gas_index_input` | Index gaz de trimis (m³) | Doar în fereastra de autoîncasare |
| `button.myengie_<loc>_gas_index_submit` | Trimite indexul gaz la ENGIE | Doar în fereastra de autoîncasare |

Fluxul de lucru pentru transmiterea indexului:
1. Setează valoarea dorită în `number.myengie_<loc>_gas_index_input` — valoarea minimă acceptată este indexul curent confirmat
2. Apasă `button.myengie_<loc>_gas_index_submit` pentru a trimite indexul către ENGIE România
3. Entitățile devin indisponibile automat în afara ferestrei de autoîncasare

> `<loc>` este derivat automat din denumirea locației sau numărul POC. Senzorii de istoric sunt generați automat pentru **anul curent** și **anul precedent**.

### Atribute senzori

**`sensor.myengie_<loc>_unpaid_invoice`** include:
- `due_date` — Data scadenței facturii neachitate
- `days_until_due` — Zile rămase până la scadență
- `overdue` — `true` dacă scadența a trecut
- `invoice_number` — Numărul facturii
- `division` — Divizia/tipul serviciului

**`sensor.myengie_<loc>_gas_index`** include:
- `next_read_start` — Începutul ferestrei pentru citirea indexului
- `next_read_end` — Sfârșitul ferestrei pentru citirea indexului

**`sensor.myengie_<loc>_last_month_m3`** include:
- `consum_gaz_kwh` — Consumul în kWh (echivalent energetic)
- `pcs` — Puterea calorifică superioară utilizată la conversie

**`sensor.myengie_<loc>_consumption_history_AAAA`** include:
- Consum lunar (m³) pentru fiecare lună disponibilă
- `total_kwh`, `average_monthly_kwh`, `average_daily_kwh`

**`sensor.myengie_<loc>_invoice_history_AAAA`** include:
- Lista completă de facturi cu sumă și dată emisie
- `total_invoices`, `total_amount_paid`, `average_monthly_amount`, `average_daily_amount`

---

## Automatizări și șabloane

Exemplu — alertă când apare o nouă factură neachitată:

```yaml
automation:
  - alias: "Factură ENGIE nouă în așteptare"
    trigger:
      - platform: template
        value_template: "{{ states('sensor.myengie_<loc>_unpaid_invoice') | float(0) > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Factură ENGIE nouă"
          message: "Ai o factură neachitată de {{ states('sensor.myengie_<loc>_unpaid_invoice') }} RON"
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
├── button.py             # Buton trimitere index gaze
├── config_flow.py        # Flux de configurare UI
├── const.py              # Constante
├── number.py             # Input index gaze
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
