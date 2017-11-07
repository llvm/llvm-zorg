if ! [ -e "${USERDIR}/config" ]; then
    echo 1>&2 "Error: 'config' file does not exist"
    echo 1>&2 "Note: Copy 'config.example' to 'config' and edit"
    exit 1
fi
