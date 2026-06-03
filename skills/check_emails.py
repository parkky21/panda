#!/usr/bin/env python3
import sys
import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

# Load environment
load_dotenv()

def main():
    sender_email = sys.argv[1] if len(sys.argv) > 1 else None

    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    imap_port = int(os.getenv("IMAP_PORT", "993"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    if not username or not password:
        print("Error: SMTP_USERNAME or SMTP_PASSWORD not set.")
        sys.exit(1)

    try:
        # Connect to IMAP with a timeout
        mail = imaplib.IMAP4_SSL(imap_server, imap_port, timeout=15)
        mail.login(username, password)
        mail.select("inbox")

        # Search for unseen messages, optionally filtering by sender
        if sender_email:
            search_query = f'(UNSEEN FROM "{sender_email}")'
        else:
            search_query = "UNSEEN"

        status, messages = mail.search(None, search_query)
        if status != "OK":
            mail.logout()
            return

        message_ids = messages[0].split()
        if not message_ids:
            mail.logout()
            return

        # Process from newest to oldest, up to a maximum of 5 emails to avoid spamming
        message_ids.reverse()
        limit = 5
        to_process = message_ids[:limit]

        print(f"📩 **Found {len(message_ids)} new unread email(s). Showing the latest {len(to_process)}:**\n")

        for msg_id in to_process:
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            if res != "OK":
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject_header = msg["Subject"]
                    if subject_header:
                        decoded = decode_header(subject_header)[0]
                        subject = decoded[0]
                        encoding = decoded[1]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")
                    else:
                        subject = "(No Subject)"
                        
                    # Decode sender
                    from_header = msg["From"]
                    if from_header:
                        decoded = decode_header(from_header)[0]
                        from_ = decoded[0]
                        encoding = decoded[1]
                        if isinstance(from_, bytes):
                            from_ = from_.decode(encoding or "utf-8", errors="ignore")
                    else:
                        from_ = "(Unknown Sender)"

                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    body = part.get_payload(decode=True).decode(errors="ignore")
                                    break
                                except Exception:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    # Limit preview length
                    body_preview = body.strip()
                    if len(body_preview) > 300:
                        body_preview = body_preview[:300] + "..."

                    print(f"👤 **From:** {from_}")
                    print(f"✉️ **Subject:** {subject}")
                    print(f"📝 **Body:** {body_preview}")
                    print("-" * 40)
                    
                    # Mark email as read
                    mail.store(msg_id, "+FLAGS", "\\Seen")

        mail.logout()

    except Exception as e:
        print(f"Error checking emails: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
