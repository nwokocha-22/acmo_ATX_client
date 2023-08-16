import time
import pickle
from pathlib import Path
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict
from helpers.loggers.errorlog import error_logger

@dataclass     
class CopyPolicy:
    """The copy Policy loads the user's Policy. 

    Note
    --------
        - [0]. A new policy config file is created if it does not already exist.
        - [1]. The loaded policy file is checked to see if the user has defaulted 
                and the time the violation occured.
        - [2]. If 24hrs has passed since violation, the restriction is relaxed.
        - [3]. If not the user is restricted from copying content to clipboard.
    """

    def has_defaulted(self) -> bool:
        """Checks if the user has violated the copy policy
        
        Returns 
        -------
            True if the User has defaulted else false 
        """
        policy = self.validate_policy()
        if policy['hasDefaulted']:
            return True
        return False

    def save_policy(self, policy:dict) -> None:
        """ Saves copy policy in the root directory """

        with open('policyConfig', 'wb') as config:
            pickle.dump(policy, config)

    def updatePolicy(self, hasDefaulted:bool=False, timeDefaulted:datetime=None) -> dict:
        """Updates the loaded copy policy.

        Parameters
        ----------
        hasDefaulted: `bool`
            Indicates if the copy policy has been violated. True if the copied content 
            size is greater than 500kb else false.

        timeDefaulted: `Datetime.time`
            The time (timestamp) the policy was violated.
        """
        policy = self._loadPolicyConfig()

        policy['hasDefaulted'] = hasDefaulted
        policy['timeDefaulted'] = timeDefaulted

        self.save_policy(policy)

        return policy

    def _createPolicyConfig(self)->None:
        """Creates and saves the policyConfig file. """
        config = {"hasDefaulted":False, "timeDefaulted":None}
        try:
            with open('policyConfig', 'xb') as logConfig:
                pickle.dump(config, logConfig)
        except FileExistsError as err:
            error_logger.exception(err)

    def get_date_difference(self, d1:datetime, d2:datetime)-> datetime:
        """Gets the difference between the current date (d2) and the date 
        
        copy policy was violated (d1).

        Parameter
        ----
        d1: `Datetime.timestamp`
        d2: `Datetime.timestamp`

        Returns:
        -------
        Datetime.timedelta object representing the number of days since the violation occurred.
        """
        d1 = datetime.strptime(d1, "%Y-%m-%d")
        d2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((d2 - d1).days)

    def checkPolicyStatus(self, policyConfig: dict ) -> Dict[str, str]:
        """Checks the time elapsed since the copy policy was violated.

        Parameter:
        ---------
            policyConfig : `dict`
                Dictionary containing the status of the copy policy.

        Note
        ----     
            -[0]. When Script is started, checks if the current user has defaulted by copying 
                  file size more than 500kb in one hour, or 1500 in 24 hours. 
            -[1]. If true, checks if it has been more than 24 hours.
            -[2]. If more than 24 hours, enables the clipboard. If less, ensures the 
                  clipboard remains disabled until next day.
        
        Returns
        -------
            policyConfig: `dict`
                A dictionary containing a boolean value for whether the copy policy is still valid.
        """
        if policyConfig["hasDefaulted"]:
            default_time = policyConfig["timeDefaulted"]
            current_time = time.time()
            d1 = datetime.fromtimestamp(default_time).strftime("%Y-%m-%d")
            d2 = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d")
            day = self.get_date_difference(d1, d2)
          
            if day >= 1:
                policyConfig['hasDefaulted'] = False
                policyConfig['timeDefaulted'] = None

                self.save_policy(policyConfig)

        return policyConfig
                

    def _loadPolicyConfig(self) -> dict:
        """Loads the policy config for writing. """

        if not Path("policyConfig").exists():
            self._createPolicyConfig()

        with open('policyConfig', 'rb') as policyConfig:
            policy_config = pickle.load(policyConfig)
        
        return policy_config

    def validate_policy(self) -> dict:
        """Loads the policy config file. Checks if policy has been violated.

         If true, check the time elapsed since the violation occured. 
         if elapsed time is more than 24 hours (1 day),
         the copy policy is reset.
        """
        _policy = self._loadPolicyConfig()
        policy = self.checkPolicyStatus(_policy)
        return policy

    def reset(self):
        """Resets the policy. """
        self.updatePolicy(hasDefaulted=False, timeDefaulted=None)


    