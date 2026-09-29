"""Run this ONCE on your own computer to get a Garmin login token.

    python scripts/login_once.py

It asks for your Garmin email and password (typed here, never saved) plus an MFA code if
your account has one, then prints a long token string. Save that string as the GitHub
secret GARMIN_TOKENS. Your password is then not needed anywhere else.
"""
import getpass

from garminconnect import Garmin

email = input("Garmin email: ").strip()
password = getpass.getpass("Garmin password (hidden): ")
client = Garmin(email, password, prompt_mfa=lambda: input("MFA code: ").strip())
client.login()
print("\nLogin OK. Copy everything between the lines into the GARMIN_TOKENS secret:\n")
print("-" * 40)
print(client.garth.dumps())
print("-" * 40)
