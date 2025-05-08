# TODO - simAI_elections

(Legenda: [x] = Completato, [P] = Parzialmente Completato, [ ] = Da Fare, [N/A] = Non Applicabile/Riconsiderato, [FIXED] = Corretto Bug/Problema Fondamentale)

**Miglioramenti Strutturali e Funzionalità Core:**
* [FIXED] Implementato ciclo di simulazione principale (`run_election_simulation` in `election.py`) e corretta integrazione con la GUI per l'avvio e la gestione dei tentativi di elezione.
* [FIXED] Corretta la logica di aggiornamento e salvataggio del budget dei candidati durante la campagna (`simulate_campaigning` in `voting.py`).
* [FIXED] Stabilito `gui.py` come punto di ingresso principale dell'applicazione.

1.  **Modelli di Votanti più Sofisticati (Citizen/Elector AI):**
    a.  [x] Personalità Complesse (Tratti base implementati).
    b.  [P] Bias Cognitivi:
        i.  [x] Effetto Bandwagon/Underdog (logica base implementata).
        ii. [x] Bias di Conferma (logica base implementata in campagna).
        iii.[x] Ragionamento Motivato (logica base implementata negli eventi).
        iv. [ ] Hindsight Bias / Altri Bias (Implementare meccanismi aggiuntivi, es. LIR - da PDF).
    c.  [x] Voto Basato su Identità vs. Policy (Implementato `party_id`, `identity_weight`, `policy_weight` e calcolo leaning combinato).
    d.  [x] Influenza Reti Sociali Esplicite (Implementato grafo Watts-Strogatz e modello influenza media pesata).
    e.  [x] Alfabetizzazione Mediatica (Aggiunto attributo e influenza base su campagna/eventi - da PDF).
    f.  [x] Apprendimento Agenti (Gli elettori del Collegio adattano i pesi policy/identità in base all'esposizione a campagna e influenza sociale).

2.  **Miglioramenti alla GUI**
    a.  [x] Visualizzazione risultati con barre.
    b.  [x] Interazioni utente base (Start, Next Round, Quit) - Ora pienamente funzionanti con il backend della simulazione.
    c.  [x] Visualizzazione Info Candidati:
        i.  [x] Rimossi sprite.
        ii. [x] Nomi colorati per genere.
        iii.[x] Visualizzazione attributi, età e partito tramite tooltip.
    d.  [x] Riepilogo finale base.
    e.  [P] Visualizzazione Avanzata Preferenze Elettori (Discussione concettuale e requisiti per GUI dedicata).
    f.  [x] Visualizzazione Elettori Chiave:
        i.  [x] Backend identifica elettori swing/influenzabili (loggati).
        ii. [x] GUI visualizza queste informazioni (nel log).
    g.  [ ] Dashboard Interattivo "What-If" (GUI complessa).
    h.  [ ] Visualizzazione Reti Sociali (GUI dedicata).

3.  **Miglioramenti alla Simulazione**
    a.  [x] Simulazione Campagna Elettorale più Complessa:
        i.  [x] Budget e temi inclusi.
        ii. [x] Legame Budget-Efficacia (Allocazione strategica budget migliorata con correzione bug, meccanica di spesa ora corretta).
        iii.[x] Rendimenti decrescenti / Impatto budget totale.
        iv. [x] Eventi Pubblici specifici (dibattiti, rally).
    b.  [x] Influenza Tratti Elettori/Cittadini (Implementata, aggiunto "Strong Partisan").
    c.  [x] Eventi Casuali:
        i.  [x] Logica base implementata (ampliata con dibattiti/rally).
        ii. [x] Eventi influenzati dallo stato, `CURRENT_HOT_TOPIC`.
        iii.[x] Applicato Motivated Reasoning & Media Literacy all'impatto.
        iv. [ ] Modellare Ecosistemi Mediatici (bias sorgenti, etc. - da PDF).
    d.  [P] Voto Strategico (Logica base implementata, migliorabile).
    e.  [N/A] Gestione Automatica Candidati Distrettuali (OK).
    f.  [ ] Implementare Sistemi Elettorali Diversi (es. RCV - da PDF).
    g.  [x] Generazione Candidati Migliorata (Genere, Unicità, Età, Attributi correlati, Partito).

4.  **Strategie di Campagna Dinamiche (Candidate AI):**
    a.  [x] Targeting Elettori (Basato su potenziale).
    b.  [x] Selezione dei Temi (Base su attributi + hot topic).
    c.  [x] Adattamento alla Competizione (Analisi avversari, adattamento temi basato su risultati precedenti e attributi candidati - implementazione base rule-based).
    d.  [ ] IA per Ottimizzazione Allocazione Risorse (Simulare CRM - da PDF).

5.  **Generazione Dinamica di Eventi/Notizie:**
    a.  [x] Eventi Casuali Influenzati (Implementati, con bias/literacy, dibattiti, rally, dipendenza da stato/hot topic; ulteriormente espandibili).

6.  **Generazione di Contenuti Testuali (NLG):**
    a.  [x] Discorsi/Oath Più Variati (Migliorata funzione).
    b.  [ ] Generazione Notizie/Post Social Media Simulati (Usare NLG - da PDF).

7.  **Integrazione Dati, Parametrizzazione e Validazione (Principi dal Documento PDF):**
    a.  [ ] Basare Agenti su Dati Reali.
    b.  [ ] Calibrazione Parametri.
    c.  [ ] Validazione Multi-Sfaccettata.

8.  **IA e LLM (Obiettivi a Lungo Termine dal Documento PDF):**
    a.  [ ] Agenti Potenziati da LLM.
    b.  [ ] Approccio Ibrido LLM/Regole.

9.  **Database SQLite (Persistenza Candidati):**
    a.  [x] Creare un database SQLite.
    b.  [x] Ogni candidato generato avrà un UUID univoco.
    c.  [x] Memorizzare tratti e valori degli attributi base per ogni candidato.
    d.  [x] Memorizzare il budget iniziale della campagna.
    e.  [x] Se viene generato un candidato con un nome nel db, utilizzare quello già presente nel db (Caricamento base implementato in generazione).
    f.  [x] Memorizzare e aggiornare il budget rimanente della campagna (Corretto in `simulate_campaigning`).
    g.  [x] Memorizzare statistiche aggregate per ogni candidato (es. vittorie, sconfitte, voti ricevuti).
    h.  [x] Aggiornare i dati del candidato nel DB al termine di ogni elezione/round rilevante (Budget e statistiche aggregate ora aggiornati).