"""Prompt 模板渲染"""

from jinja2 import Template


def render_template(template_str: str, **kwargs) -> str:
    """渲染 Jinja2 模板"""
    tmpl = Template(template_str)
    return tmpl.render(**kwargs)
