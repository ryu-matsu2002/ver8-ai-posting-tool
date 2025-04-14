# app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

# ✅ ログインフォーム
class LoginForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired()])

# ✅ 自動投稿フォーム（CSRF保護付き）
class AutoPostForm(FlaskForm):
    site_id = SelectField("投稿先サイト", coerce=int, validators=[DataRequired()])
    keywords = TextAreaField("キーワード一覧", validators=[DataRequired()])
    template_id = SelectField("テンプレート", coerce=int, validators=[DataRequired()])
    submit = SubmitField("記事生成を開始")
