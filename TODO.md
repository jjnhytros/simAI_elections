# TODO.md
# TODO - simAI_elections

(Legenda: [x] = Completato, [P] = Parzialmente Completato, [ ] = Da Fare, [N/A] = Non Applicabile/Riconsiderato)

1.  **Modelli di Votanti più Sofisticati (Citizen/Elector AI):**
    * [x] Personalità Complesse (Tratti base implementati).
    * [P] Bias Cognitivi:
        * [P] Effetto Bandwagon/Underdog (logica base implementata).
        * [P] Bias di Conferma (logica base implementata in campagna).
        * [P] Ragionamento Motivato (logica base implementata negli eventi).
        * [ ] Hindsight Bias / Altri Bias (Implementare meccanismi aggiuntivi, es. LIR - da PDF).
    * [P] Voto Basato su Identità vs. Policy (Implementato `party_id`, `identity_weight` e calcolo leaning combinato).
    * [P] Influenza Reti Sociali Esplicite (Implementato grafo Watts-Strogatz e modello influenza media pesata).
    * [P] Alfabetizzazione Mediatica (Aggiunto attributo e influenza base su campagna/eventi - da PDF).
    * [P] Apprendimento Agenti (Gli elettori del Collegio possono adattare leggermente i pesi policy/identità in base all'esposizione a campagna e influenza sociale).

2.  **Miglioramenti alla GUI**
    * [x] Visualizzazione risultati con barre.
    * [x] Interazioni utente base (Start, Next Round, Quit).
    * [P] Visualizzazione Info Candidati:
        * [x] Rimossi sprite.
        * [x] Nomi colorati per genere.
        * [P] Visualizzazione attributi, età e partito tramite tooltip.
    * [x] Riepilogo finale base.
    * [ ] Visualizzazione Avanzata Preferenze Elettori (Mappa/distribuzione leanings - richiede GUI dedicata).
    * [P] Visualizzazione Elettori Chiave:
        * [P] Backend identifica elettori swing/influenzabili (loggati).
        * [ ] GUI deve visualizzare queste informazioni.
    * [ ] Dashboard Interattivo "What-If" (GUI complessa).
    * [ ] Visualizzazione Reti Sociali (GUI dedicata).

3.  **Miglioramenti alla Simulazione**
    * [P] Simulazione Campagna Elettorale più Complessa:
        * [x] Budget e temi inclusi.
        * [P] Legame Budget-Efficacia (Allocazione strategica budget).
        * [ ] Rendimenti decrescenti / Impatto budget totale.
        * [ ] Eventi Pubblici specifici (dibattiti, rally).
    * [x] Influenza Tratti Elettori/Cittadini (Implementata, aggiunto "Strong Partisan").
    * [P] Eventi Casuali:
        * [x] Logica base implementata.
        * [P] Eventi influenzati dallo stato, `CURRENT_HOT_TOPIC`.
        * [P] Applicato Motivated Reasoning & Media Literacy all'impatto.
        * [ ] Modellare Ecosistemi Mediatici (bias sorgenti, etc. - da PDF).
    * [P] Voto Strategico (Logica base implementata).
    * [N/A] Gestione Automatica Candidati Distrettuali (OK).
    * [ ] Implementare Sistemi Elettorali Diversi (es. RCV - da PDF).
    * [x] Generazione Candidati Migliorata (Genere, Unicità, Età, Attributi correlati, Partito).

4.  **Strategie di Campagna Dinamiche (Candidate AI):**
    * [P] Targeting Elettori (Basato su potenziale).
    * [P] Selezione dei Temi (Base su attributi + hot topic).
    * [P] Adattamento alla Competizione (Analisi avversari, adattamento temi basato su risultati precedenti e attributi candidati - implementazione base rule-based).
    * [ ] IA per Ottimizzazione Allocazione Risorse (Simulare CRM - da PDF).

5.  **Generazione Dinamica di Eventi/Notizie:**
    * [P] Eventi Casuali Influenzati (Implementati, con bias/literacy).

6.  **Generazione di Contenuti Testuali (NLG):**
    * [P] Discorsi/Oath Più Variati (Migliorata funzione).
    * [ ] Generazione Notizie/Post Social Media Simulati (Usare NLG - da PDF).

7.  **Integrazione Dati, Parametrizzazione e Validazione (Principi dal Documento PDF):**
    * [ ] Basare Agenti su Dati Reali.
    * [ ] Calibrazione Parametri.
    * [ ] Validazione Multi-Sfaccettata.

8.  **IA e LLM (Obiettivi a Lungo Termine dal Documento PDF):**
    * [ ] Agenti Potenziati da LLM.
    * [ ] Approccio Ibrido LLM/Regole.