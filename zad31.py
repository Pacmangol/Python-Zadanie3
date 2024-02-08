"""
Program do obliczania różnicy kursowej i pozostałej kwoty do zapłaty dla faktur i ich płatności.

Klasy:
- Invoice: Reprezentuje fakturę.
- Payment: Reprezentuje płatność.

Funkcje:
- pobierz_kurs(data, waluta, typ_daty): Pobiera kurs waluty dla danej daty z API NBP.
- calculate_difference(invoice, payments): Oblicza różnicę kursową dla danej faktury i jej płatności.
- calculate_remaining_amount(invoice, payments): Oblicza pozostałą kwotę do zapłaty dla danej faktury.
- wprowadz_walute(): Prosi użytkownika o wprowadzenie waluty.
- wprowadz_date(typ_daty): Prosi użytkownika o wprowadzenie daty.
- wprowadz_date_po(prompt, data_wystawienia): Prosi użytkownika o wprowadzenie daty, która jest późniejsza niż data wystawienia faktury.
- wprowadz_kwote(prompt): Prosi użytkownika o wprowadzenie kwoty.
- pytanie_tak_nie(prompt): Prosi użytkownika o odpowiedź na pytanie tak/nie.

Główna pętla programu prosi użytkownika o wprowadzenie szczegółów faktury i płatności, oblicza różnicę kursową i pozostałą kwotę do zapłaty dla każdej faktury, a następnie pyta, czy użytkownik chce wprowadzić kolejną fakturę.
"""

import os
import requests
import json
import datetime
import time
import pandas as pd

class Invoice:
    def __init__(self, invoice_number, amount, currency, issue_date):
        self.invoice_number = invoice_number
        self.amount = amount
        self.currency = currency
        self.issue_date = issue_date

class Payment:
    def __init__(self, invoice_number, amount, currency, payment_date):
        self.invoice_number = invoice_number
        self.amount = amount
        self.currency = currency
        self.payment_date = payment_date

def pobierz_kurs(data, waluta):
    if waluta == 'PLN':
        return 1.0
    data_dt = datetime.datetime.strptime(data, '%Y-%m-%d')
    earliest_data = datetime.datetime(2002, 1, 2)  # Data, od której dostępne są dane w API NBP
    retry_counter = 0  # Dodajemy licznik prób
    while data_dt >= earliest_data and retry_counter < 3:  # Dodajemy warunek na licznik prób
        try:
            communication = requests.get(f'http://api.nbp.pl/api/exchangerates/rates/c/{waluta}/{data_dt.strftime('%Y-%m-%d')}/?format=json')
            response = communication.json()
            return response['rates'][0]['bid']
        except Exception as e:
            print(f"Błąd podczas pobierania kursu waluty, szukam dzień wcześniej")
            data_dt -= datetime.timedelta(days=1)  # Próbuj z poprzednim dniem
            retry_counter += 1  # Zwiększamy licznik prób
    print(f"Nie można znaleźć kursu waluty dla daty wcześniejszej niż {earliest_data.strftime('%Y-%m-%d')}")
    return None

def calculate_difference(invoice, payments):
    total_difference = 0
    for payment in payments:
        if payment.invoice_number != invoice.invoice_number:
            continue
        invoice_rate = pobierz_kurs(invoice.issue_date, invoice.currency)
        payment_rate = pobierz_kurs(payment.payment_date, invoice.currency)
        if invoice_rate is None or payment_rate is None:
            return None
        print(f"Kurs wymiany dla dnia wystawienia faktury: {invoice_rate}")
        print(f"Kurs wymiany dla dnia płatności: {payment_rate}")
        total_difference += round((payment_rate - invoice_rate) , 4)
    return total_difference

def calculate_remaining_amount(invoice, payments):
    total_payment_in_pln = 0
    for payment in payments:
        if payment.invoice_number != invoice.invoice_number:
            continue
        payment_rate = pobierz_kurs(payment.payment_date, payment.currency)
        if payment_rate is None:
            return None
        total_payment_in_pln += payment.amount * payment_rate
    invoice_rate = pobierz_kurs(invoice.issue_date, invoice.currency)
    if invoice_rate is None:
        return None
    return round((invoice.amount * invoice_rate) - total_payment_in_pln , 2)

def wprowadz_walute():
    for _ in range(3):
        waluta = input("Podaj walutę (PLN, USD, EUR, GBP): ").upper()
        if waluta in available_currencies:
            return waluta
        else:
            print("Nieobsługiwana waluta. Dostępne waluty to: " + ', '.join(available_currencies))
    print("Przekroczono limit prób wprowadzenia waluty.")
    return None

def wprowadz_date(typ_daty):
    for _ in range(3):
        data = input(f"Podaj datę {typ_daty} (YYYY-MM-DD): ")
        try:
            datetime.datetime.strptime(data, '%Y-%m-%d')
            return data
        except ValueError:
            print("Niepoprawny format daty. Proszę użyć formatu YYYY-MM-DD.")
    print("Przekroczono limit prób wprowadzenia daty.")
    return None

def wprowadz_date_po(prompt, data_wystawienia):
    while True:
        data = wprowadz_date(prompt)
        if data is None:
            return None
        if datetime.datetime.strptime(data, '%Y-%m-%d') >= datetime.datetime.strptime(data_wystawienia, '%Y-%m-%d'):
            return data
        else:
            print("Data płatności musi być późniejsza niż data wystawienia faktury. Proszę wprowadzić poprawną datę.")

def wprowadz_kwote(prompt):
    while True:
        try:
            kwota = float(input(prompt))
            if kwota < 0:
                print("Kwota nie może być ujemna. Proszę wprowadzić dodatnią kwotę.")
            else:
                return kwota
        except ValueError:
            print("Niepoprawna kwota. Proszę wprowadzić liczbę.")

def pytanie_tak_nie(prompt):
    while True:
        odpowiedz = input(prompt).lower()
        if odpowiedz in ['tak', 't', 'nie', 'n']:
            return odpowiedz in ['tak', 't']
        else:
            print("Niepoprawna odpowiedź. Proszę odpowiedzieć 'tak', 'nie', 't', 'n', 'TAK', 'NIE', 'T', 'N'.")

def zapisz_do_excel(invoices, payments):
    df_invoices = pd.DataFrame([vars(invoice) for invoice in invoices])
    df_payments = pd.DataFrame([vars(payment) for payment in payments])
    df_invoices.to_excel('faktury.xlsx', index=False)
    df_payments.to_excel('platnosci.xlsx', index=False)

def odczytaj_z_excel():
    df_invoices = pd.read_excel('faktury.xlsx')
    df_payments = pd.read_excel('platnosci.xlsx')
    invoices = [Invoice(row.invoice_number, row.amount, row.currency, row.issue_date) for _, row in df_invoices.iterrows()]
    payments = [Payment(row.invoice_number, row.amount, row.currency, row.payment_date) for _, row in df_payments.iterrows()]
    return invoices, payments

# Get the available currencies from the environment variable
available_currencies = os.getenv('AVAILABLE_CURRENCIES', 'PLN,USD,EUR,GBP').split(',')

invoices, payments = odczytaj_z_excel()

while True:
    # Użytkownik wprowadza numer faktury, datę i kwotę zapłaty
    invoice_number = input("Podaj numer faktury: ")
    invoice_issue_date = wprowadz_date('wystawienia faktury')
    if invoice_issue_date is None:
        continue
    payment_date = wprowadz_date_po('płatności', invoice_issue_date)
    if payment_date is None:
        continue
    payment_amount = wprowadz_kwote("Podaj kwotę zapłaty: ")
    payment_currency = wprowadz_walute()
    if payment_currency is None:
        continue

    payments.append(Payment(invoice_number, payment_amount, payment_currency, payment_date))

    for invoice in invoices:
        if invoice.invoice_number == invoice_number:
            print("Różnica kursowa dla faktury numer " + invoice_number + ": " + str(calculate_difference(invoice, payments)))
            print("Kwota pozostała do zapłaty: " + str(calculate_remaining_amount(invoice, payments)))
            break
    else:
        invoice_amount = wprowadz_kwote("Podaj kwotę faktury: ")
        invoice_currency = wprowadz_walute()
        if invoice_currency is None:
            continue
        invoices.append(Invoice(invoice_number, invoice_amount, invoice_currency, invoice_issue_date))

        print("Różnica kursowa dla nowej faktury numer " + invoice_number + ": " + str(calculate_difference(invoices[-1], payments)))
        print("Kwota pozostała do zapłaty: " + str(calculate_remaining_amount(invoices[-1], payments)))

    # Pytaj użytkownika, czy chce wprowadzić kolejną fakturę
    next_invoice = pytanie_tak_nie("Czy chcesz wprowadzić kolejną fakturę? (tak/nie): ")
    if not next_invoice:
        break

zapisz_do_excel(invoices, payments)

