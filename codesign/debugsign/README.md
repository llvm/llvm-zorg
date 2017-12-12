# LLDB Codesigning Identities

The **`debugsign`** tool contains the logic necessary to configure
and enable automation-friendly codesigning for LLDB builds on Darwin
systems.

The **import** sub-command requires a P12 archive containing a
codesigning identity. A P12 archive compatible with the
**`debugsign`** tool can produced using the following procedure:

# Generating a Codesigning Identity

* Open **Keychain Access**
* -> **App Menu**
* -> **Certificate Assistant**
* -> **Create a Certificate**

In the dialog that appears:

* Name: **`lldb_codesign`**
* Certificate Type: **`Code Signing`**
* use defaults for all other values and complete the dialog sequence

The identity (private key, public key, self-signed certificate) will
be created in the default login keychain. Export the identity:

* Select **login** keychain
* Select **My Certificates**
* Select entire **lldb_codesign** item (not sub-components)
* **File** -> **Export Items**
* Select File Format: **`Personal Information Exchange (.p12)`**
* When asked for a password to protect the exported archive, enter
  **`lldb_codesign`** for both options.
* If **Keychain Access** asks for permission to export, click **Allow**

The resulting ``.p12`` file can be passed to **`debugsign`**'s import
sub-command.

# Using the debugsign Script

Once you've created the **`.p12`** archive, you can use it to enable
codesigning on any number of machines for as long as the generated
certificate is valid.

The general use case for ``debugsign`` is described in the script's
help output: **`debugsign help`**

