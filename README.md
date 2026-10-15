# Cloud Explorer: TL;DR

Laboratorio de AWS Academy Cloud Foundations (módulos 3, 4 y 6).
Completa los 6 `TODO` de `__main__.py` usando **boto3**, el SDK de AWS para Python.

## Configuración

1. **Arrancar el lab:** AWS Academy → Learner Lab → **Start Lab** → espera a que el punto se ponga verde.
2. **Preparar el entorno:**
   ```powershell
   .venv\Scripts\Activate.ps1
   pip install boto3 python-dotenv
   pip install "boto3-stubs[ec2,sts,iam]"   # optional: boto3 autocompletion in VS Code
   ```
   - En VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → `.venv\Scripts\python.exe`.
   - Tras instalar los stubs: `Ctrl+Shift+P` → **Developer: Reload Window**.
3. **Crear `.env`:**
   - Copia `.env.example` como `.env`.
   - Pega los valores de **AWS Details → AWS CLI → Show**:
     ```
     AWS_ACCESS_KEY_ID=...
     AWS_SECRET_ACCESS_KEY=...
     AWS_SESSION_TOKEN=...     ← largo, cópialo entero
     AWS_DEFAULT_REGION=us-east-1
     ```
4. **Ejecutar:**
   ```powershell
   python __main__.py --offline                     # part 3 only, no AWS
   python __main__.py                               # parts 1, 2 and 3
   python __main__.py --launch --student TuNombre   # + part 4 (EC2)
   ```

> ⚠️ Las credenciales **caducan** con cada sesión del lab (unas 4 h). Si aparece `ExpiredToken`, pega las nuevas en `.env`.
> `.env` está en `.gitignore`: **nunca** lo subas a Git.

## Partes y conceptos

Orden recomendado: **3 → 1 → 2 → 4**.

### Parte 1: Regiones y AZs (TODO 1 y 2)
- **Región:** zona geográfica (`us-east-1`, `eu-south-2`).
- **AZ (zona de disponibilidad):** centro de datos aislado dentro de una región. Sirven para tener alta disponibilidad.
- `ZoneName` (`us-east-1a`) cambia de una cuenta a otra. `ZoneId` (`use1-az1`) es la ubicación física real.
- **TODO 1:** `describe_regions()["Regions"]` → `RegionName` → `sorted(...)`.
- **TODO 2:** `describe_availability_zones()["AvailabilityZones"]` → tuplas `(ZoneName, ZoneId)`.

### Parte 2: ¿Quién soy? (TODO 3)
- **STS** te dice qué identidad hay detrás de tus credenciales.
- `user/...` → usuario IAM con claves **permanentes**.
- `assumed-role/...` → rol con claves **temporales**. Es lo que verás en el lab.
- **TODO 3:** `sts.get_caller_identity()` → devuelve `Account`, `Arn` y `UserId`.

### Parte 3: Evaluador de políticas IAM (TODO 4, offline)
- IAM revisa **todas** las sentencias de **todas** las políticas:
  1. Si aplica algún **Deny** → `ExplicitDeny`. El Deny siempre gana.
  2. Si no, y aplica algún **Allow** → `Allow`.
  3. Si no aplica nada → `ImplicitDeny`. Por defecto, todo está denegado.
- Usa `_statement_applies()`, que ya está hecha.
- ⚠️ No devuelvas `Allow` en cuanto encuentres el primero: puede haber un Deny después.
- ✅ Los 4 tests deben salir `[OK ]`.

### Parte 4: Ciclo de vida de EC2 (TODO 5 y 6, opcional)
- Estados: `pending → running → shutting-down → terminated`.
- **AMI:** la imagen del sistema operativo. **User data:** script que se ejecuta en el primer arranque. **Tags:** etiquetas para identificar recursos.
- **TODO 5:** `create_instances(ImageId, InstanceType="t3.micro", MinCount=1, MaxCount=1, UserData, TagSpecifications)`.
- **TODO 6:** `terminate()` + `wait_until_terminated()`. Mejor dentro de un `finally`, para que se ejecute aunque algo falle.
- La web no abre desde el navegador porque el security group bloquea el puerto 80.

## Consejos boto3
- `client(...)` devuelve **diccionarios**. Haz `print()` de la respuesta para ver su estructura.
- `resource(...)` devuelve **objetos** con atributos y métodos (`instance.id`, `instance.terminate()`).
- Sin `boto3-stubs`, VS Code no autocompleta `ec2.` ni `sts.`: boto3 crea sus métodos en tiempo de ejecución, así que Pylance no puede verlos.

## Errores frecuentes
| Error | Solución |
|---|---|
| `NoCredentialsError` | Comprueba que `.env` existe y tiene las 3 claves |
| `ExpiredToken` | Reinicia el lab y pega las credenciales nuevas |
| `UnauthorizedOperation` | Usa solo `us-east-1` o `us-west-2` |
| `NotImplementedError` | Normal: te falta ese TODO |
| `TypeError: exceptions must derive from BaseException` | Cambiaste solo `NotImplementedError` y dejaste `raise`: sustituye la línea entera por un `return` |
| `ModuleNotFoundError` | `pip install boto3 python-dotenv` con el venv activo |
