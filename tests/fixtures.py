# fixtures.py - sample forms as the add-on would see them via the a11y tree.
# The seed of the battery that real web markup will later be fed into.

from matcher import FieldDescriptor as F
from controls import ControlDescriptor as C


# A multilingual messy form. Each field names the real-world case it models.
MESSY_MULTILINGUAL_FORM = [
    F(label="Email address", name="email"),                 # en, clean -> strong
    F(label="Adresse e-mail"),                              # fr label -> strong
    F(label="Telefonnummer"),                               # de phone -> strong
    F(label="Apellidos"),                                   # es surname -> strong
    F(label="الاسم الاول"),                                  # ar first name -> strong
    F(label="Pays", autocomplete="country"),                # fr label, but ac wins
    F(label="", autocomplete="given-name"),                 # no label, ac only
    F(label="", placeholder="First name"),                  # placeholder -> guess
    F(label="", id="field_9x"),                             # unlabelled -> none
    F(label="Why do you want this role?"),                  # bespoke -> none
]

# Choice controls, one of each kind we classify.
CHOICE_CONTROLS = {
    "native_select": C(role="combobox", states=("focusable",), option_count=195),
    "aria_combobox": C(role="combobox", states=("focusable", "haspopup"), option_count=0),
    "editable_combobox": C(role="combobox", states=("editable",),
                           autocomplete="list", option_count=195),
    "async_combobox": C(role="combobox", states=("editable",),
                        autocomplete="list", option_count=0),
    "multiselect": C(role="listbox", states=("focusable", "multiselectable")),
    "radio": C(role="radiobutton", states=("focusable", "checkable")),
    "checkbox": C(role="checkbox", states=("focusable", "checkable")),
    "datepicker": C(role="datepicker"),
    "text": C(role="edit", states=("editable",)),
}

# Country option lists as they appear in forms of different languages.
COUNTRY_OPTIONS_EN = ["France", "Germany", "United Kingdom", "Spain"]
COUNTRY_OPTIONS_FR = ["Allemagne", "Espagne", "France", "Royaume-Uni"]
COUNTRY_OPTIONS_AR = ["فرنسا", "المانيا", "المملكة المتحدة", "اسبانيا"]
