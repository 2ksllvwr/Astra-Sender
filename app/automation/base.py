from abc import ABC, abstractmethod

class AutomationProvider(ABC):
    @abstractmethod
    def send(self, profile: dict, message: str | None, mode: str) -> None:
        '''Executa o envio conforme o perfil e o modo configurados.'''
        raise NotImplementedError
