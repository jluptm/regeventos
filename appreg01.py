import streamlit as st
import libsql_client as libsql
import asyncio
import re

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Registro de Participantes",
    page_icon="📝",
    layout="centered",
)

# ── DISEÑO Y ESTILOS PERSONALIZADOS (Aesthetic Premium) ──────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Fondo degradado oscuro premium */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    color: #f8fafc;
}

/* Título principal con gradiente */
.main-title {
    background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.5rem;
    text-align: center;
    margin-bottom: 0.5rem;
}

/* Subtítulo */
.subtitle {
    color: #94a3b8;
    font-size: 1rem;
    text-align: center;
    margin-bottom: 2rem;
}

/* Tarjeta del Formulario */
.form-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 30px;
    backdrop-filter: blur(16px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    margin-bottom: 2rem;
}

/* Inputs personalizados */
div[data-baseweb="input"] {
    background-color: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 10px !important;
    transition: all 0.3s ease !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 10px rgba(99, 102, 241, 0.4) !important;
}

/* Botón principal */
.stButton > button {
    background: linear-gradient(90deg, #6366f1, #a855f7) !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.3s ease !important;
    width: 100%;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
}

.stButton > button:hover {
    opacity: 0.95 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* Separador elegante */
hr {
    border-color: rgba(255, 255, 255, 0.08) !important;
    margin: 2rem 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── LOGO DE LA APLICACIÓN ────────────────────────────────────────────────────
col_space1, col_logo, col_space2 = st.columns([1, 2, 1])
with col_logo:
    try:
        st.image("assets/logo integridad cristiana seminario.png", width=220)
    except FileNotFoundError:
        st.markdown("<h3 style='text-align: center;'>⛪</h3>", unsafe_allow_html=True)

st.markdown('<div class="main-title">Registro de Participantes</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ingresa tus datos para registrarte en el Seminario Taller La Integridad Cristiana</div>', unsafe_allow_html=True)

# ── FUNCIÓN PARA OBTENER EL CLIENTE DE TURSO ─────────────────────────────────
def get_turso_credentials():
    try:
        url = st.secrets["turso"]["url_re"]
        auth_token = st.secrets["turso"]["auth_token_re"]
        
        # Normalizar el protocolo a https:// para evitar errores de websocket con libsql
        if url.startswith("libsql://"):
            url = url.replace("libsql://", "https://")
        elif url.startswith("wss://"):
            url = url.replace("wss://", "https://")
            
        return url, auth_token
    except KeyError:
        st.error("❌ Error: No se encontraron las credenciales de Turso (`url_re` y `auth_token_re`) en `.streamlit/secrets.toml`.")
        st.stop()

# ── FUNCIÓN ASÍNCRONA PARA INICIALIZAR LA TABLA Y REGISTRAR DATOS ──────────────
async def init_db(url, auth_token):
    """Crea la tabla en Turso si aún no existe."""
    async with libsql.create_client(url=url, auth_token=auth_token) as client:
        await client.execute("""
            CREATE TABLE IF NOT EXISTS registros_usuarios_fhurtado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombres TEXT NOT NULL,
                apellidos TEXT NOT NULL,
                iglesia TEXT,
                cargo TEXT,
                email TEXT,
                telefono TEXT,
                fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nombres, apellidos, email, telefono)
            );
        """)

async def check_existing_record(url, auth_token, data):
    """Verifica si ya existe un registro con la misma combinación de nombres, apellidos, email y teléfono."""
    async with libsql.create_client(url=url, auth_token=auth_token) as client:
        sql = """
            SELECT 1 FROM registros_usuarios_fhurtado 
            WHERE nombres = ? 
              AND apellidos = ? 
              AND (email = ? OR (email IS NULL AND ? IS NULL))
              AND (telefono = ? OR (telefono IS NULL AND ? IS NULL))
            LIMIT 1
        """
        res = await client.execute(sql, [
            data["nombres"],
            data["apellidos"],
            data["email"],
            data["email"],
            data["telefono"],
            data["telefono"]
        ])
        return len(res.rows) > 0

async def save_to_turso(url, auth_token, data):
    """Guarda los datos del usuario en Turso."""
    async with libsql.create_client(url=url, auth_token=auth_token) as client:
        sql = """
            INSERT INTO registros_usuarios_fhurtado (nombres, apellidos, iglesia, cargo, email, telefono)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await client.execute(sql, [
            data["nombres"],
            data["apellidos"],
            data["iglesia"],
            data["cargo"],
            data["email"],
            data["telefono"]
        ])

# Inicializar Base de Datos en segundo plano
url, auth_token = get_turso_credentials()
try:
    asyncio.run(init_db(url, auth_token))
except Exception as e:
    st.error(f"Error al conectar con la base de datos Turso: {e}")

# ── FORMULARIO DE REGISTRO ────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    
    # Fila 1: Nombres y Apellidos
    col_nombres, col_apellidos = st.columns(2)
    with col_nombres:
        nombres = st.text_input("Nombres *", placeholder="Ej: Juan Carlos")
    with col_apellidos:
        apellidos = st.text_input("Apellidos *", placeholder="Ej: Pérez Gómez")
        
    # Fila 2: Iglesia y Cargo
    col_iglesia, col_cargo = st.columns(2)
    with col_iglesia:
        iglesia = st.text_input("Iglesia *", placeholder="Ej: Iglesia Central")
    with col_cargo:
        cargo = st.text_input("Cargo *", placeholder="Ej: Diácono, Pastor, Miembro")
        
    # Fila 3: Email y Teléfono
    col_email, col_telf_container = st.columns(2)
    with col_email:
        email = st.text_input("Email (Opcional)", placeholder="Ej: juan.perez@email.com")
        
    with col_telf_container:
        st.markdown("<label style='font-size: 0.9rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: block;'>Teléfono (WhatsApp) *</label>", unsafe_allow_html=True)
        col_pais, col_op, col_num = st.columns([1.5, 1, 2.5])
        
        paises = {
            "Venezuela (+58)": "+58",
            "Colombia (+57)": "+57",
            "Brasil (+55)": "+55",
            "República Dominicana (+1)": "+1",
            "Cuba (+53)": "+53",
            "USA (+1)": "+1"
        }
        
        with col_pais:
            pais_sel = st.selectbox("País", list(paises.keys()), label_visibility="collapsed")
            cod_pais = paises[pais_sel]
            
        if cod_pais == "+58":
            with col_op:
                operadora = st.selectbox("Operadora", ["412", "422", "414", "424", "416", "426"], label_visibility="collapsed")
            with col_num:
                num_telf = st.text_input("Número (7 dígitos)", placeholder="Ej: 1234567", label_visibility="collapsed")
        else:
            with col_op:
                st.selectbox("Operadora", ["N/A"], disabled=True, label_visibility="collapsed")
                operadora = ""
            with col_num:
                num_telf = st.text_input("Número completo", placeholder="Ej: 3001234567", label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón de enviar
    submit = st.button("Enviar Registro")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ── LÓGICA DE VALIDACIÓN Y ENVÍO ──────────────────────────────────────────────
if submit:
    # Validaciones básicas
    nombres_clean = nombres.strip()
    apellidos_clean = apellidos.strip()
    iglesia_clean = iglesia.strip()
    cargo_clean = cargo.strip()
    email_clean = email.strip()
    
    # Procesar número de teléfono
    num_telf_digits = re.sub(r"\D", "", num_telf.strip())
    if cod_pais == "+58":
        telefono_completo = f"{cod_pais}{operadora}{num_telf_digits}"
    else:
        telefono_completo = f"{cod_pais}{num_telf_digits}"
        
    errors = []
    
    if not nombres_clean:
        errors.append("El campo 'Nombres' es obligatorio.")
    if not apellidos_clean:
        errors.append("El campo 'Apellidos' es obligatorio.")
    if not iglesia_clean:
        errors.append("El campo 'Iglesia' es obligatorio.")
    if not cargo_clean:
        errors.append("El campo 'Cargo' es obligatorio.")
    if not num_telf_digits:
        errors.append("El campo 'Teléfono' es obligatorio.")
    else:
        # Validación extra de teléfono según país
        if cod_pais == "+58" and len(num_telf_digits) != 7:
            errors.append("Para Venezuela, el número de teléfono debe tener exactamente 7 dígitos (ej: 1234567).")
        elif (cod_pais == "+1") and len(num_telf_digits) != 10:
            errors.append("Para USA o República Dominicana, el número de teléfono debe tener exactamente 10 dígitos.")
            
    if email_clean:
        # Validación simple de email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email_clean):
            errors.append("Por favor ingresa un formato de email válido.")
            
    if errors:
        for err in errors:
            st.error(f"⚠️ {err}")
    else:
        # Registrar en la base de datos
        datos_registro = {
            "nombres": nombres_clean,
            "apellidos": apellidos_clean,
            "iglesia": iglesia_clean,
            "cargo": cargo_clean,
            "email": email_clean if email_clean else None,
            "telefono": telefono_completo
        }
        
        with st.spinner("Guardando registro en la base de datos Turso..."):
            try:
                # Comprobar si ya existe el registro
                existe = asyncio.run(check_existing_record(url, auth_token, datos_registro))
                if existe:
                    st.warning("⚠️ Ya existe un participante registrado con este mismo Nombre, Apellido, Email y Teléfono.")
                else:
                    asyncio.run(save_to_turso(url, auth_token, datos_registro))
                    st.balloons()
                    st.success("🎉 ¡Registro guardado exitosamente!")
                    
                    # Mostrar resumen del registro guardado
                    st.markdown(f"""
                    ### Resumen de tu Registro:
                    * **Nombre Completo:** {nombres_clean} {apellidos_clean}
                    * **Iglesia:** {iglesia_clean}
                    * **Cargo:** {cargo_clean}
                    * **Email:** {email_clean if email_clean else '_No especificado_'}
                    * **Teléfono:** {telefono_completo}
                    """)
            except Exception as e:
                st.error(f"❌ Ocurrió un error al guardar en la base de datos: {e}")

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#64748b; font-size:0.85rem;">Prondamin 2026 · Módulo de Registro y Control</p>',
    unsafe_allow_html=True,
)
