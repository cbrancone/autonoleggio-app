from datetime import datetime


class Veicolo:
    """Rappresenta un singolo veicolo nel parco auto."""

    def __init__(
        self,
        targa: str,
        marca: str,
        modello: str,
        categoria: str,
        prezzo_giornaliero: float,
    ):
        self.targa = targa.upper()
        self.marca = marca
        self.modello = modello
        self.categoria = categoria  # es. Economica, SUV, Lusso
        self.prezzo_giornaliero = prezzo_giornaliero
        self.disponibile = True

    def __str__(self):
        stato = "DISPONIBILE" if self.disponibile else "NOLEGGIATO"
        return (
            f"[{self.targa}] {self.marca} {self.modello} ({self.categoria}) "
            f"- €{self.prezzo_giornaliero:.2f}/giorno | Stato: {stato}"
        )


class Noleggio:
    """Rappresenta un noleggio effettuato da un cliente."""

    def __init__(self, veicolo: Veicolo, nome_cliente: str, giorni: int):
        self.veicolo = veicolo
        self.nome_cliente = nome_cliente
        self.giorni = giorni
        self.data_inizio = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Calcolo dei costi
        self.prezzo_base = veicolo.prezzo_giornaliero * giorni
        self.percentuale_sconto = self._calcola_sconto(giorni)
        self.sconto_applicato = self.prezzo_base * (
            self.percentuale_sconto / 100
        )
        self.costo_totale = self.prezzo_base - self.sconto_applicato

    def _calcola_sconto(self, giorni: int) -> int:
        """Applica uno sconto in percentuale per noleggi prolungati."""
        if giorni >= 30:
            return 20  # 20% di sconto oltre 1 mese
        elif giorni >= 7:
            return 10  # 10% di sconto oltre 1 settimana
        elif giorni >= 3:
            return 5  # 5% di sconto oltre 3 giorni
        return 0

    def stampa_ricevuta(self):
        print("\n" + "=" * 45)
        print("           RICEVUTA DI NOLEGGIO")
        print("=" * 45)
        print(f"Data transazione : {self.data_inizio}")
        print(f"Cliente          : {self.nome_cliente}")
        print(
            f"Veicolo          : {self.veicolo.marca} {self.veicolo.modello} ({self.veicolo.targa})"
        )
        print(f"Giorni noleggio  : {self.giorni}")
        print("-" * 45)
        print(f"Tariffa al giorno: €{self.veicolo.prezzo_giornaliero:.2f}")
        print(f"Totale lordo     : €{self.prezzo_base:.2f}")
        if self.percentuale_sconto > 0:
            print(
                f"Sconto applicato : -{self.percentuale_sconto}% (-€{self.sconto_applicato:.2f})"
            )
        else:
            print("Sconto applicato : Nessuno")
        print("-" * 45)
        print(f"TOTALE DA PAGARE : €{self.costo_totale:.2f}")
        print("=" * 45 + "\n")


class GestoreAutonoleggio:
    """Gestisce la flotta e i processi di noleggio e restituzione."""

    def __init__(self):
        self.parco_auto = {}
        self.noleggi_attivi = {}

    def aggiungi_veicolo(
        self,
        targa: str,
        marca: str,
        modello: str,
        categoria: str,
        prezzo: float,
    ):
        targa = targa.upper()
        if targa in self.parco_auto:
            print(f"Errore: Un veicolo con targa {targa} esiste già.")
            return
        self.parco_auto[targa] = Veicolo(
            targa, marca, modello, categoria, prezzo
        )
        print(f"Veicolo [{targa}] aggiunto con successo.")

    def mostra_veicoli(self, solo_disponibili: bool = False):
        if not self.parco_auto:
            print("Nessun veicolo presente nel sistema.")
            return

        print("\n--- FLOTTA VEICOLI ---")
        trovati = False
        for veicolo in self.parco_auto.values():
            if solo_disponibili and not veicolo.disponibile:
                continue
            print(veicolo)
            trovati = True

        if solo_disponibili and not trovati:
            print("Nessun veicolo attualmente disponibile.")

    def noleggia_veicolo(self, targa: str, nome_cliente: str, giorni: int):
        targa = targa.upper()
        veicolo = self.parco_auto.get(targa)

        if not veicolo:
            print("Errore: Veicolo non trovato.")
            return
        if not veicolo.disponibile:
            print("Errore: Il veicolo è già stato noleggiato.")
            return
        if giorni <= 0:
            print("Errore: Il numero di giorni deve essere maggiore di 0.")
            return

        veicolo.disponibile = False
        noleggio = Noleggio(veicolo, nome_cliente, giorni)
        self.noleggi_attivi[targa] = noleggio

        print("\nNoleggio completato con successo!")
        noleggio.stampa_ricevuta()

    def restituisci_veicolo(self, targa: str):
        targa = targa.upper()
        veicolo = self.parco_auto.get(targa)

        if not veicolo:
            print("Errore: Veicolo non trovato.")
            return
        if veicolo.disponibile:
            print("Errore: Questo veicolo non risulta attualmente noleggiato.")
            return

        veicolo.disponibile = True
        noleggio = self.noleggi_attivi.pop(targa)
        print(
            f"Veicolo [{targa}] restituito da {noleggio.nome_cliente}. Ora è nuovamente disponibile."
        )


def main():
    gestore = GestoreAutonoleggio()

    # Pre-caricamento parco auto iniziale per test
    gestore.aggiungi_veicolo(
        "AA123BB", "Fiat", "Panda", "Economica", 35.0
    )
    gestore.aggiungi_veicolo("CC456DD", "Ford", "Focus", "Compatta", 50.0)
    gestore.aggiungi_veicolo("EE789FF", "Audi", "Q5", "SUV", 95.0)

    while True:
        print("\n" + "#" * 35)
        print("  GESTIONALE AUTONOLEGGIO - MENU")
        print("#" * 35)
        print("1. Mostra veicoli DISPONIBILI")
        print("2. Mostra TUTTI i veicoli")
        print("3. Aggiungi nuovo veicolo")
        print("4. Avvia un noleggio (calcola costo)")
        print("5. Restituisci veicolo")
        print("6. Esci")

        scelta = input("\nSeleziona un'opzione (1-6): ").strip()

        if scelta == "1":
            gestore.mostra_veicoli(solo_disponibili=True)

        elif scelta == "2":
            gestore.mostra_veicoli(solo_disponibili=False)

        elif scelta == "3":
            try:
                targa = input("Targa: ").strip()
                marca = input("Marca: ").strip()
                modello = input("Modello: ").strip()
                categoria = input(
                    "Categoria (es. Economica, SUV): "
                ).strip()
                prezzo = float(
                    input("Prezzo giornaliero (€): ").replace(",", ".")
                )
                gestore.aggiungi_veicolo(
                    targa, marca, modello, categoria, prezzo
                )
            except ValueError:
                print("Errore: Inserisci un valore numerico per il prezzo.")

        elif scelta == "4":
            try:
                targa = input("Targa veicolo da noleggiare: ").strip()
                cliente = input("Nome e cognome cliente: ").strip()
                giorni = int(input("Numero di giorni di noleggio: "))
                gestore.noleggia_veicolo(targa, cliente, giorni)
            except ValueError:
                print(
                    "Errore: Inserisci un valore intero per il numero di giorni."
                )

        elif scelta == "5":
            targa = input("Targa del veicolo da restituire: ").strip()
            gestore.restituisci_veicolo(targa)

        elif scelta == "6":
            print("Uscita dal programma in corso. Arrivederci!")
            break

        else:
            print("Scelta non valida. Riprova.")


if __name__ == "__main__":
    main()
