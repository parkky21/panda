import os

class AgentConfig:
    """
    Manages environment and settings configuration for the Panda Agent.
    """
    @staticmethod
    def get_model_id() -> str:
        return os.getenv("MODEL_ID", "moonshotai.kimi-k2.5")

    @staticmethod
    def get_aws_region() -> str:
        return os.getenv("AWS_REGION", "us-east-1")

    @staticmethod
    def get_telegram_token() -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @staticmethod
    def get_whatsapp_token() -> str:
        return os.getenv("WHATSAPP_TOKEN", "")

    @staticmethod
    def get_whatsapp_phone_number_id() -> str:
        return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    @staticmethod
    def get_whatsapp_verify_token() -> str:
        return os.getenv("WHATSAPP_VERIFY_TOKEN", "")

    @staticmethod
    def get_discord_token() -> str:
        return os.getenv("DISCORD_BOT_TOKEN", "")

