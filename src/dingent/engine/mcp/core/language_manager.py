import gettext
from importlib import resources
from typing import Literal


class LanguageManager:
    """一个简单的类来加载和缓存 gettext 翻译对象。"""

    def __init__(self, locale_dir, domain, supported_langs, fallback_lang: Literal["en-US", "zh-CN"] = "en-US"):
        self.locale_dir = locale_dir
        self.domain = domain
        self.supported_langs = supported_langs
        self.fallback_lang: Literal["en-US", "zh-CN"] = fallback_lang
        self._translations = {}
        self._init_translators()

    def _init_translators(self):
        for lang in self.supported_langs:
            translation = gettext.translation(self.domain, self.locale_dir, languages=[lang])
            self._translations[lang] = translation

    def get_translator(self, lang: Literal["en-US", "zh-CN"] = "en-US"):
        """
        根据语言代码获取该语言的 gettext 翻译函数。
        """
        if lang not in self.supported_langs:
            lang = self.fallback_lang

        if lang in self._translations:
            return self._translations[lang].gettext
        raise ValueError(f"Unsupported language: {lang}. Supported languages are: {self.supported_langs}")


locales_path = str(resources.files("mcp_servers.resources").joinpath("locales"))

# 在你的应用启动时，初始化一个全局的语言管理器
language_manager = LanguageManager(
    locale_dir=locales_path,
    domain="messages",
    supported_langs=["en-US", "zh-CN"],
    fallback_lang="en-US",
)
