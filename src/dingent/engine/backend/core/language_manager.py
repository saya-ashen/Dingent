import gettext
from pathlib import Path
from typing import Literal


class LanguageManager:
    """一个简单的类来加载和缓存 gettext 翻译对象。"""

    def __init__(self, domain, supported_langs, fallback_lang: Literal["en-US", "zh-CN"] = "en-US"):
        self.domain = domain
        self.supported_langs = supported_langs
        self.fallback_lang: Literal["en-US", "zh-CN"] = fallback_lang
        self._translations = {}
        self._init_translators()

    def _init_translators(self):
        app_localedir = Path(__file__).parent.parent / "locales"
        for lang in self.supported_langs:
            framework_translation = gettext.translation("messages", app_localedir, languages=[lang])
            user_translation = gettext.translation(
                domain=self.domain, localedir=str(Path.cwd() / "locales"), languages=[lang], fallback=True
            )
            user_translation.add_fallback(framework_translation)
            self._translations[lang] = user_translation

    def get_translator(self, lang: Literal["en-US", "zh-CN"] = "en-US"):
        """
        根据语言代码获取该语言的 gettext 翻译函数。
        """
        if lang not in self.supported_langs:
            lang = self.fallback_lang

        if lang in self._translations:
            return self._translations[lang].gettext
        raise ValueError(f"Unsupported language: {lang}. Supported languages are: {self.supported_langs}")


language_manager = LanguageManager(
    domain="messages",
    supported_langs=["en-US", "zh-CN"],
    fallback_lang="en-US",
)
