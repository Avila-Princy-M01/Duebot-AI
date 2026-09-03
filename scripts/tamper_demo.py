"""Tamper demo helper script.

Usage:
    python scripts/tamper_demo.py          # Tampers Block #11 in audit_log
    python scripts/tamper_demo.py --revert # Restores Block #11
"""

import argparse
import sqlite3
import subprocess
import sys

ORIGINAL_BACKUP_TABLE = "_audit_log_backup"


def main() -> None:
    parser = argparse.ArgumentParser(description="Tamper audit_log for live demo")
    parser.add_argument("--revert", action="store_true", help="Revert the tampered row")
    args = parser.parse_args()

    con = sqlite3.connect("duebot.db")
    cur = con.cursor()

    if args.revert:
        # Check if backup exists
        cur.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
            (ORIGINAL_BACKUP_TABLE,),
        )
        if cur.fetchone()[0] == 0:
            print("[INFO] No backup found. Re-seeding database to restore clean chain...")
            subprocess.run(
                [sys.executable, "scripts/seed_db.py", "--num-invoices", "260"],
                check=True,
            )
            print("[RESTORED] Database clean and chain verified!")
            return

        cur.execute(f"SELECT rowid, reasoning_summary FROM {ORIGINAL_BACKUP_TABLE} LIMIT 1")
        row = cur.fetchone()
        if row:
            rowid, original_text = row
            cur.execute(
                "UPDATE audit_log SET reasoning_summary=? WHERE rowid=?",
                (original_text, rowid),
            )
            cur.execute(f"DROP TABLE {ORIGINAL_BACKUP_TABLE}")
            con.commit()
            print(f"[RESTORED] Block #{rowid} restored to original text.")
            print("[STATUS] SHA-256 cryptographic chain is valid again! Refresh /audit to verify.")
            return

    # Backup original row before tampering
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {ORIGINAL_BACKUP_TABLE} "
        f"(rowid INTEGER PRIMARY KEY, reasoning_summary TEXT)"
    )
    cur.execute(f"DELETE FROM {ORIGINAL_BACKUP_TABLE}")
    cur.execute("SELECT rowid, reasoning_summary FROM audit_log LIMIT 1 OFFSET 10")
    row = cur.fetchone()
    if not row:
        print("[ERROR] audit_log is empty! Run 'python scripts/seed_db.py' first.")
        return

    rowid, original_text = row
    cur.execute(f"INSERT INTO {ORIGINAL_BACKUP_TABLE} VALUES (?, ?)", (rowid, original_text))

    # Tamper the row
    tampered_text = "Attacker altered reasoning note (forged entry)"
    cur.execute(
        "UPDATE audit_log SET reasoning_summary=? WHERE rowid=?",
        (tampered_text, rowid),
    )
    con.commit()
    con.close()

    print("\n========================================================")
    print("🚨 TAMPER APPLIED SUCCESSFULLY!")
    print("--------------------------------------------------------")
    print(f"Target Row    : Block #{rowid}")
    print(f"Corrupted Text: '{tampered_text}'")
    print("Result        : SHA-256 hash avalanche broke the chain.")
    print("Next Step     : In browser, go to /audit and click 'Verify Chain'")
    print("To Revert     : python scripts/tamper_demo.py --revert")
    print("========================================================\n")


if __name__ == "__main__":
    main()
