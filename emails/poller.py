import asyncio
from emails.services import fetch_emails

class EmailPoller:
    def __init__(self, server: str, email_user: str, email_pass: str, interval: int = 60):
        self.server = server
        self.email_user = email_user
        self.email_pass = email_pass
        self.interval = interval
        self.emails = []
        self._task = None
        self._running = False
        self._loop = asyncio.get_event_loop()

    async def _poll(self):
        while self._running:
            try:
                new_emails = await fetch_emails(self.server, self.email_user, self.email_pass)
                for email in new_emails:
                    if email not in self.emails:
                        self.emails.append(email)
                print(f"{len(new_emails)} mail çekildi. Toplam: {len(self.emails)}")
            except Exception as e:
                print(f"Polling hatası: {str(e)}")
            await asyncio.sleep(self.interval)

    def start(self):
        if not self._running:
            self._running = True
            if self._loop.is_running():
                self._task = self._loop.create_task(self._poll())
            else:
                self._loop.run_until_complete(self._poll())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def get_emails(self):
        return self.emails
