"""
国际化(i18n)支持模块
提供多语言翻译功能
"""
import gettext
import locale
import os
from pathlib import Path
from typing import Optional

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '中文 (简体)',
    'en_US': 'English (US)',
}

# 当前语言设置
_current_language: Optional[str] = None
_translator: Optional[gettext.GNUTranslations] = None

def get_locales_dir() -> Path:
    """获取本地化文件目录"""
    return Path(__file__).parent / 'locales'

def detect_system_language() -> str:
    """检测系统语言"""
    try:
        # 获取系统语言设置
        system_lang = locale.getdefaultlocale()[0]
        if system_lang and system_lang in SUPPORTED_LANGUAGES:
            return system_lang
        
        # 尝试从环境变量获取
        for env_var in ['LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG']:
            lang = os.environ.get(env_var)
            if lang:
                # 提取语言代码 (如: zh_CN.UTF-8 -> zh_CN)
                lang_code = lang.split('.')[0].split(':')[0]
                if lang_code in SUPPORTED_LANGUAGES:
                    return lang_code
                
    except Exception:
        pass
    
    # 默认英语
    return 'en_US'

def set_language(lang_code: Optional[str] = None) -> bool:
    """
    设置语言
    
    Args:
        lang_code: 语言代码，如 'zh_CN'。如果为 None 则自动检测
    
    Returns:
        是否设置成功
    """
    global _current_language, _translator
    
    if lang_code is None:
        lang_code = detect_system_language()
    
    if lang_code not in SUPPORTED_LANGUAGES:
        lang_code = 'en_US'
    
    try:
        locales_dir = get_locales_dir()
        
        # 加载翻译文件
        if lang_code != 'en_US':  # 英语是默认语言，不需要翻译文件
            translation = gettext.translation(
                'grub-theme',
                localedir=str(locales_dir),
                languages=[lang_code],
                fallback=True
            )
        else:
            # 使用空翻译（返回原始字符串）
            translation = gettext.NullTranslations()
        
        _translator = translation
        _current_language = lang_code
        
        # 设置全局翻译函数
        translation.install()
        
        return True
        
    except Exception as e:
        # 如果加载失败，使用英语作为后备
        _translator = gettext.NullTranslations()
        _current_language = 'en_US'
        _translator.install()
        return False

def get_current_language() -> str:
    """获取当前语言"""
    return _current_language or 'en_US'

def get_language_name(lang_code: str) -> str:
    """获取语言显示名称"""
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)

def _(message: str) -> str:
    """
    翻译函数
    
    Args:
        message: 要翻译的消息
    
    Returns:
        翻译后的消息
    """
    if _translator:
        return _translator.gettext(message)
    return message

def ngettext(singular: str, plural: str, n: int) -> str:
    """
    复数形式翻译函数
    
    Args:
        singular: 单数形式
        plural: 复数形式
        n: 数量
    
    Returns:
        翻译后的消息
    """
    if _translator:
        return _translator.ngettext(singular, plural, n)
    return singular if n == 1 else plural

# 初始化国际化
def init_i18n(lang_code: Optional[str] = None) -> None:
    """
    初始化国际化系统
    
    Args:
        lang_code: 指定语言代码，如果为 None 则自动检测
    """
    set_language(lang_code)

# 自动初始化
if _current_language is None:
    init_i18n()