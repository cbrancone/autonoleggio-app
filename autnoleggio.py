Ecco una struttura completa in Python per gestire un software di autonoleggio da riga di comando. Utilizza la programmazione a oggetti (OOP) ed è facilmente estendibile.

### Codice (`autonoleggio.py`)

```python
import sys


class Auto:

    def __init__(self, targa: str, marca: str, modello: str, prezzo_giornaliero: float):
        self.targa = targa.upper()
        self.marca = marca
        self.modello = modello
        self.prezzo_giornaliero = prezzo_giornaliero
        self.disponibile = True

    def __str__(self):
        stato = "Disponibile" if self.disponibile else "Noleggiata"
        return f"[{self.targa}] {self.marca} {self.modello} - {self.prezzo_giornaliero:.2f}€/giorno ({stato})"


class Noleggio:

    def __init__(self, auto: Auto, cliente: str, giorni: int):
        self.auto = auto
        self.cliente = cliente
        self.giorni = giorni
        self.costo_totale = auto.prezzo_giornaliero * giorni


class GestoreAutonoleggio:

    def __init__(self, nome_azienda: str):
        self.nome_azienda = nome_azienda
        self.flotta: dict[str, Auto] = {}
        self.noleggi_attivi: list[Noleggio] = []

    def aggiungi_auto(self, targa: str, marca: str, modello: str, prezzo: float) -> bool:
        targa = targa.upper()
        if targa in self.flotta:
            print(f"⚠️ Errore: Un'auto con targa {targa} esiste già nel sistema.")
            return False

        nuova_auto = Auto(targa, marca, modello, prezzo)
        self.flotta[targa] = nuova_auto
        print(f"✅ Auto aggiunta: {nuova_auto}")
        return True

    def mostra_flotta(self, solo_disponibili: bool = False):
        print(f"\n--- Parco Auto ('{self.nome_azienda}') ---")
        auto_da_mostrare = [
            a for a in self.flotta.values() if not solo_disponibili or a.disponibile
        ]

        if not auto_da_mostrare:
            print("Nessuna auto trovata.")
            return

        for auto in auto_da_mostrare:
            print(f"  • {auto}")

    def noleggia_auto(self, targa: str, cliente: str, giorni: int) -> bool:
        targa = targa.upper()
        auto = self.flotta.get(targa)

        if not auto:
            print("⚠️ Errore: Targa non trovata nel sistema.")
            return False

        if not auto.disponibile:
            print(f"⚠️ Errore: L'auto {auto.marca} {auto.modello} non è al momento disponibile.")
            return False

        auto.disponibile = False
        noleggio = Noleggio(auto, cliente, giorni)
        self.noleggi_attivi.append(noleggio)

        print(f"\n🎉 Noleggio confermato!")
        print(f"  Cliente: {cliente}")
        print(f"  Veicolo: {auto.marca} {auto.modello} ({auto.targa})")
        print(f"  Durata: {giorni} giorni")
        print(f"  Totale da pagare: {noleggio.costo_totale:.2f}€")
        return True

    def restituisci_auto(self, targa: str) -> bool:
        targa = targa.upper()
        auto = self.flotta.get(targa)

        if not auto:
            print("⚠️ Errore: Targa non trovata.")
            return False

        if auto.disponibile:
            print("⚠️ Errore: Questo veicolo risulta già presente in sede.")
            return False

        # Rimuove dai noleggi attivi e rende l'auto disponibile
        auto.disponibile = True
        self.noleggi_attivi = [n for n in self.noleggi_attivi if n.auto.targa != targa]

        print(f"✅ Veicolo {auto.targa} restituito con successo e rientrato in flotta.")
        return True


def menu_principale():
    sistema = GestoreAutonoleggio("EasyRent Italia")

    # Dati di prova iniziali
    sistema.aggiungi_auto("AA123BB", "Fiat", "500", 35.00)
    sistema.aggiungi_auto("CC456DD", "BMW", "Serie 1", 75.00)
    sistema.aggiungi_auto("EE789FF", "Alfa Romeo", "Tonale", 90.00)

    while True:
        print("\n" + "=" * 40)
        print(f"   GESTIONE AUTONOLEGGIO - {sistema.nome_azienda.upper()}")
        print("=" * 40)
        print("1. Visualizza tutte le auto")
        print("2. Visualizza solo auto disponibili")
        print("3. Aggiungi una nuova auto")
        print("4. Noleggia un'auto")
        print("5. Restituisci un'auto")
        print("0. Esci")

        scelta = input("\nSeleziona un'opzione (0-5): ").strip()

        if scelta == "1":
            sistema.mostra_flotta()

        elif scelta == "2":
            sistema.mostra_flotta(solo_disponibili=True)

        elif scelta == "3":
            targa = input("Targa: ")
            marca = input("Marca: ")
            modello = input("Modello: ")
            try:
                prezzo = float(input("Prezzo giornaliero (€): "))
                sistema.aggiungi_auto(targa, marca, modello, prezzo)
            except ValueError:
                print("⚠️ Errore: Inserisci un importo numerico valido.")

        elif scelta == "4":
            sistema.mostra_flotta(solo_disponibili=True)
            targa = input("\nInserisci la targa dell'auto da noleggiare: ")
            cliente = input("Nome e cognome cliente: ")
            try:
                giorni = int(input("Numero di giorni di noleggio: "))
                if giorni <= 0:
                    print("⚠️ Il numero di giorni deve essere maggiore di 0.")
                    continue
                sistema.noleggia_auto(targa, cliente, giorni)
            except ValueError:
                print("⚠️ Errore: Inserisci un numero intero di giorni.")

        elif scelta == "5":
            targa = input("Inserisci la targa dell'auto da restituire: ")
            sistema.restituisci_auto(targa)

        elif scelta == "0":
            print("\nChiusura del programma. Arrivederci!")
            sys.exit()

        else:
            print("⚠️ Opzione non valida, riprova.")


if __name__ == "__main__":
    menu_principale()

```

---

### Funzionalità incluse

* **Gestione Flotta:** Aggiunta di nuovi veicoli e controllo sovrascrittura targhe.
* **Stato dei Veicoli:** Tracciamento della disponibilità in tempo reale.
* **Calcolo Costi:** Calcolo automatico del totale in base al prezzo giornaliero e al numero di giorni.
* **Interfaccia CLI:** Menu interattivo guidato da riga di comando.