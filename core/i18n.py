import json
from pathlib import Path
from string import Template

import core.settings as settings


class Locale:

    def __init__(self, lang: str):
        self.path = Path(f"./i18n/{lang}.json")
        self.data = {}
        self.load()

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            d = f.read()
            self.data = json.loads(d)
            f.close()

    def get_string(self, key: str):
        n = self.data.get(key, None)
        if n != None:
            return n
        return self.t("i18n.not_found", name=key)

    def t(self, key: str, *args, **kwargs):
        """
        使用变量字典替换模板字符串中的变量。
        - 【参数】模板字符串：`包含要替换的变量的模板字符串`。

        - 【参数】替换的变量：`要在模板字符串中替换的变量`。

        - 返回结果：`替换了变量的模板字符串`。
        """
        template = Template(self.get_string(key))
        replaced_str = template.safe_substitute(*args, **kwargs)
        return replaced_str


locale = Locale(settings.LANGUAGE)
