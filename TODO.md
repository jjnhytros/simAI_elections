# TODO - simAI_elections

(Legenda: [x] = Completato, [P] = Parzialmente Completato, [ ] = Da Fare, [N/A] = Non Applicabile/Riconsiderato, [FIXED] = Corretto Bug/Problema Fondamentale)

**Miglioramenti Strutturali e Funzionalità Core:**
* [FIXED] Implementato ciclo di simulazione principale (`run_election_simulation` in `election.py`) e corretta integrazione con la GUI per l'avvio e la gestione dei tentativi di elezione.
* [FIXED] Corretta la logica di aggiornamento e salvataggio del budget dei candidati durante la campagna (`simulate_campaigning` in `voting.py`).
* [FIXED] Stabilito `gui.py` come punto di ingresso principale dell'applicazione.

1.  **Modelli di Votanti più Sofisticati (Citizen/Elector AI):**
    * [x] Personalità Complesse (Tratti base implementati).
    * [P] Bias Cognitivi:
        * [x] Effetto Bandwagon/Underdog (logica base implementata).
        * [x] Bias di Conferma (logica base implementata in campagna).
        * [x] Ragionamento Motivato (logica base implementata negli eventi).
        * [ ] Hindsight Bias / Altri Bias (Implementare meccanismi aggiuntivi, es. LIR - da PDF).
    * [x] Voto Basato su Identità vs. Policy (Implementato `party_id`, `identity_weight` e calcolo leaning combinato).
    * [x] Influenza Reti Sociali Esplicite (Implementato grafo Watts-Strogatz e modello influenza media pesata).
    * [x] Alfabetizzazione Mediatica (Aggiunto attributo e influenza base su campagna/eventi - da PDF).
    * [P] Apprendimento Agenti (Gli elettori del Collegio possono adattare leggermente i pesi policy/identità in base all'esposizione a campagna e influenza sociale).

2.  **Miglioramenti alla GUI**
    * [x] Visualizzazione risultati con barre.
    * [x] Interazioni utente base (Start, Next Round, Quit) - Ora pienamente funzionanti con il backend della simulazione.
    * [x] Visualizzazione Info Candidati:
        * [x] Rimossi sprite.
        * [x] Nomi colorati per genere.
        * [x] Visualizzazione attributi, età e partito tramite tooltip.
    * [P] Riepilogo finale base (migliorabile con più dettagli post-elezione).
    * [ ] Visualizzazione Avanzata Preferenze Elettori (Discussione concettuale e requisiti per GUI dedicata).
    * [P] Visualizzazione Elettori Chiave:
        * [x] Backend identifica elettori swing/influenzabili (loggati).
        * [ ] GUI deve visualizzare queste informazioni.
    * [ ] Dashboard Interattivo "What-If" (GUI complessa).
    * [ ] Visualizzazione Reti Sociali (GUI dedicata).

3.  **Miglioramenti alla Simulazione**
    * [P] Simulazione Campagna Elettorale più Complessa:
        * [x] Budget e temi inclusi.
        * [P] Legame Budget-Efficacia (Allocazione strategica budget migliorata con correzione bug, meccanica di spesa ora corretta).
        * [ ] Rendimenti decrescenti / Impatto budget totale.
        * [ ] Eventi Pubblici specifici (dibattiti, rally).
    * [x] Influenza Tratti Elettori/Cittadini (Implementata, aggiunto "Strong Partisan").
    * [P] Eventi Casuali:
        * [x] Logica base implementata.
        * [P] Eventi influenzati dallo stato, `CURRENT_HOT_TOPIC`.
        * [x] Applicato Motivated Reasoning & Media Literacy all'impatto.
        * [ ] Modellare Ecosistemi Mediatici (bias sorgenti, etc. - da PDF).
    * [x] Voto Strategico (Logica base implementata).
    * [N/A] Gestione Automatica Candidati Distrettuali (OK).
    * [ ] Implementare Sistemi Elettorali Diversi (es. RCV - da PDF).
    * [x] Generazione Candidati Migliorata (Genere, Unicità, Età, Attributi correlati, Partito).

4.  **Strategie di Campagna Dinamiche (Candidate AI):**
    * [x] Targeting Elettori (Basato su potenziale).
    * [x] Selezione dei Temi (Base su attributi + hot topic).
    * [x] Adattamento alla Competizione (Analisi avversari, adattamento temi basato su risultati precedenti e attributi candidati - implementazione base rule-based).
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

9.  **Database SQLite (Persistenza Candidati):**
    * [x] Creare un database SQLite.
    * [x] Ogni candidato generato avrà un UUID univoco.
    * [x] Memorizzare tratti e valori degli attributi base per ogni candidato.
    * [x] Memorizzare il budget iniziale della campagna.
    * [x] Se viene generato un candidato con un nome nel db, utilizzare quello già presente nel db (Caricamento base implementato in generazione).
    * [x] Memorizzare e aggiornare il budget rimanente della campagna (Corretto in `simulate_campaigning`).
    * [ ] Memorizzare statistiche aggregate per ogni candidato (es. vittorie, sconfitte, voti ricevuti).
    * [P] Aggiornare i dati del candidato nel DB al termine di ogni elezione/round rilevante (Budget aggiornato durante la campagna, altre statistiche da implementare).