from skeLCS.OfflineEnvironment import OfflineEnvironment
from skeLCS.ClassifierSet import ClassifierSet
from skeLCS.Classifier import Classifier
from skeLCS.Prediction import Prediction
from skeLCS.Timer import Timer
from skeLCS.IterationRecord import IterationRecord

from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.metrics import balanced_accuracy_score
import random
import numpy as np
import math
import time
import pickle
import copy

class eLCS(BaseEstimator,ClassifierMixin, RegressorMixin):
    def __init__(self, learningIterations=10000, trackAccuracyWhileFit = False, N=1000, p_spec=0.5, discreteAttributeLimit=10,
                 specifiedAttributes = np.array([]), nu=5, chi=0.8, upsilon=0.04, theta_GA=25, theta_del=20, theta_sub=20,
                 acc_sub=0.99, beta=0.2, delta=0.1, init_fit=0.01, fitnessReduction=0.1, doCorrectSetSubsumption=False,
                 doGASubsumption=True, selectionMethod='tournament', theta_sel=0.5, randomSeed = "none",matchForMissingness=False,
                 rebootFilename=None):

        '''
        :param learningIterations:      Must be nonnegative integer. The number of training cycles to run.
        :param trackAccuracyWhileFit:   Must be boolean. Determines if accuracy is tracked during model training
        :param N:                       Must be nonnegative integer. Maximum micro classifier population size (sum of classifier numerosities).
        :param p_spec:                  Must be float from 0 - 1. Probability of specifying an attribute during the covering procedure. Advised: larger amounts of attributes => lower p_spec values
        :param discreteAttributeLimit:  Must be nonnegative integer OR "c" OR "d". Multipurpose param. If it is a nonnegative integer, discreteAttributeLimit determines the threshold that determines
                                        if an attribute will be treated as a continuous or discrete attribute. For example, if discreteAttributeLimit == 10, if an attribute has more than 10 unique
                                        values in the dataset, the attribute will be continuous. If the attribute has 10 or less unique values, it will be discrete. Alternatively,
                                        discreteAttributeLimit can take the value of "c" or "d". See next param for this.
        :param specifiedAttributes:     Must be an ndarray type of nonnegative integer attributeIndices (zero indexed).
                                        If "c", attributes specified by index in this param will be continuous and the rest will be discrete. If "d", attributes specified by index in this
                                        param will be discrete and the rest will be continuous.
                                        If this value is given, and discreteAttributeLimit is not "c" or "d", discreteAttributeLimit overrides this specification
        :param nu:                      (v) Must be a float. Power parameter used to determine the importance of high accuracy when calculating fitness. (typically set to 5, recommended setting of 1 in noisy data)
        :param chi:                     (X) Must be float from 0 - 1. The probability of applying crossover in the GA. (typically set to 0.5-1.0)
        :param upsilon:                 (u) Must be float from 0 - 1. The probability of mutating an allele within an offspring.(typically set to 0.01-0.05)
        :param theta_GA:                Must be nonnegative float. The GA threshold. The GA is applied in a set when the average time (# of iterations) since the last GA in the correct set is greater than theta_GA.
        :param theta_del:               Must be a nonnegative integer. The deletion experience threshold; The calculation of the deletion probability changes once this threshold is passed.
        :param theta_sub:               Must be a nonnegative integer. The subsumption experience threshold
        :param acc_sub:                 Must be float from 0 - 1. Subsumption accuracy requirement
        :param beta:                    Must be float. Learning parameter; Used in calculating average correct set size
        :param delta:                   Must be float. Deletion parameter; Used in determining deletion vote calculation.
        :param init_fit:                Must be float. The initial fitness for a new classifier. (typically very small, approaching but not equal to zero)
        :param fitnessReduction:        Must be float. Initial fitness reduction in GA offspring rules.
        :param doCorrectSetSubsumption: Must be boolean. Determines if subsumption is done in [C] after [C] updates.
        :param doGASubsumption:         Must be boolean. Determines if subsumption is done between offspring and parents after GA
        :param selectionMethod:         Must be either "tournament" or "roulette". Determines GA selection method. Recommended: tournament
        :param theta_sel:               Must be float from 0 - 1. The fraction of the correct set to be included in tournament selection.
        :param randomSeed:              Must be an integer or "none". Set a constant random seed value to some integer (in order to obtain reproducible results). Put 'none' if none (for pseudo-random algorithm runs).
        :param matchForMissingness:     Must be boolean. Determines if eLCS matches for missingness (i.e. if a missing value can match w/ a specified value)
        :param rebootFilename:          Must be String or None. Filename of pickled model to be rebooted
        '''

        '''
        Parameter Validity Checking
        Checks all parameters for valid values
        '''
        #learningIterations
        if not self.checkIsInt(learningIterations):
            raise Exception("learningIterations param must be nonnegative integer")

        if learningIterations < 0:
            raise Exception("learningIterations param must be nonnegative integer")

        #trackAccuracyWhileFit
        if not(isinstance(trackAccuracyWhileFit,bool)):
            raise Exception("trackAccuracyWhileFit param must be boolean")

        #N
        if not self.checkIsInt(N):
            raise Exception("N param must be nonnegative integer")

        if N < 0:
            raise Exception("N param must be nonnegative integer")

        #p_spec
        if not self.checkIsFloat(p_spec):
            raise Exception("p_spec param must be float from 0 - 1")

        if p_spec < 0 or p_spec > 1:
            raise Exception("p_spec param must be float from 0 - 1")

        #discreteAttributeLimit
        if discreteAttributeLimit != "c" and discreteAttributeLimit != "d":
            try:
                dpl = int(discreteAttributeLimit)
                if not self.checkIsInt(discreteAttributeLimit):
                    raise Exception("discreteAttributeLimit param must be nonnegative integer or 'c' or 'd'")
                if dpl < 0:
                    raise Exception("discreteAttributeLimit param must be nonnegative integer or 'c' or 'd'")
            except:
                raise Exception("discreteAttributeLimit param must be nonnegative integer or 'c' or 'd'")

        #specifiedAttributes
        if not (isinstance(specifiedAttributes,np.ndarray)):
            raise Exception("specifiedAttributes param must be ndarray")

        for spAttr in specifiedAttributes:
            if not self.checkIsInt(spAttr):
                raise Exception("All specifiedAttributes elements param must be nonnegative integers")
            if int(spAttr) < 0:
                raise Exception("All specifiedAttributes elements param must be nonnegative integers")

        #nu
        if not self.checkIsFloat(nu):
            raise Exception("nu param must be float")

        #chi
        if not self.checkIsFloat(chi):
            raise Exception("chi param must be float from 0 - 1")

        if chi < 0 or chi > 1:
            raise Exception("chi param must be float from 0 - 1")

        #upsilon
        if not self.checkIsFloat(upsilon):
            raise Exception("upsilon param must be float from 0 - 1")

        if upsilon < 0 or upsilon > 1:
            raise Exception("upsilon param must be float from 0 - 1")

        #theta_GA
        if not self.checkIsFloat(theta_GA):
            raise Exception("theta_GA param must be nonnegative float")

        if theta_GA < 0:
            raise Exception("theta_GA param must be nonnegative float")

        #theta_del
        if not self.checkIsInt(theta_del):
            raise Exception("theta_del param must be nonnegative integer")

        if theta_del < 0:
            raise Exception("theta_del param must be nonnegative integer")

        #theta_sub
        if not self.checkIsInt(theta_sub):
            raise Exception("theta_sub param must be nonnegative integer")

        if theta_sub < 0:
            raise Exception("theta_sub param must be nonnegative integer")

        #acc_sub
        if not self.checkIsFloat(acc_sub):
            raise Exception("acc_sub param must be float from 0 - 1")

        if acc_sub < 0 or acc_sub > 1:
            raise Exception("acc_sub param must be float from 0 - 1")

        #beta
        if not self.checkIsFloat(beta):
            raise Exception("beta param must be float")

        #delta
        if not self.checkIsFloat(delta):
            raise Exception("delta param must be float")

        #init_fit
        if not self.checkIsFloat(init_fit):
            raise Exception("init_fit param must be float")

        #fitnessReduction
        if not self.checkIsFloat(fitnessReduction):
            raise Exception("fitnessReduction param must be float")

        #doCorrectSetSubsumption
        if not(isinstance(doCorrectSetSubsumption,bool)):
            raise Exception("doCorrectSetSubsumption param must be boolean")

        # doGASubsumption
        if not (isinstance(doGASubsumption, bool)):
            raise Exception("doGASubsumption param must be boolean")

        #selectionMethod
        if selectionMethod != "tournament" and selectionMethod != "roulette":
            raise Exception("selectionMethod param must be 'tournament' or 'roulette'")

        #theta_sel
        if not self.checkIsFloat(theta_sel):
            raise Exception("theta_sel param must be float from 0 - 1")

        if theta_sel < 0 or theta_sel > 1:
            raise Exception("theta_sel param must be float from 0 - 1")

        #randomSeed
        if randomSeed != "none":
            try:
                if not self.checkIsInt(randomSeed):
                    raise Exception("randomSeed param must be integer or 'none'")
                random.seed(int(randomSeed))
                np.random.seed(int(randomSeed))
            except:
                raise Exception("randomSeed param must be integer or 'none'")

        #matchForMissingness
        if not (isinstance(matchForMissingness, bool)):
            raise Exception("matchForMissingness param must be boolean")

        # rebootPopulationFilename
        if rebootFilename != None and not isinstance(rebootFilename, str):
            raise Exception("rebootFilename param must be None or String from pickle")
        '''
        Set params
        '''
        self.learningIterations = learningIterations
        self.N = N
        self.p_spec = p_spec
        self.discreteAttributeLimit = discreteAttributeLimit
        self.specifiedAttributes = specifiedAttributes
        self.trackAccuracyWhileFit = trackAccuracyWhileFit
        self.nu = nu
        self.chi = chi
        self.upsilon = upsilon
        self.theta_GA = theta_GA
        self.theta_del = theta_del
        self.theta_sub = theta_sub
        self.acc_sub = acc_sub
        self.beta = beta
        self.delta = delta
        self.init_fit = init_fit
        self.fitnessReduction = fitnessReduction
        self.doCorrectSetSubsumption = doCorrectSetSubsumption
        self.doGASubsumption = doGASubsumption
        self.selectionMethod = selectionMethod
        self.theta_sel = theta_sel
        self.randomSeed = randomSeed
        self.matchForMissingness = matchForMissingness

        '''
        Set tracking tools
        '''
        self.trackingObj = tempTrackingObj()
        self.record = IterationRecord()
        self.hasTrained = False
        self.rebootFilename = rebootFilename

    def checkIsInt(self,num):
        try:
            n = float(num)
            if num - int(num) == 0:
                return True
            else:
                return False
        except:
            return False

    def checkIsFloat(self,num):
        try:
            n = float(num)
            return True
        except:
            return False

    ##*************** Fit ****************
    def fit(self, X, y):
        """Scikit-learn required: Supervised training of eLCS

        Parameters
        X: array-like {n_samples, n_features} Training instances. ALL INSTANCE ATTRIBUTES MUST BE NUMERIC or NAN
        y: array-like {n_samples} Training labels. ALL INSTANCE PHENOTYPES MUST BE NUMERIC NOT NAN OR OTHER TYPE

        Returns self
        """
        #If trained already, raise Exception
        if self.hasTrained:
            raise Exception("Cannot train already trained model again")

        # Check if X and Y are numeric
        try:
            for instance in X:
                for value in instance:
                    if not (np.isnan(value)):
                        float(value)
            for value in y:
                float(value)

        except:
            raise Exception("X and y must be fully numeric")

        #Set up environment
        self.env = OfflineEnvironment(X,y,self)

        self.explorIter = 0

        self.trackingAccuracy = []
        self.movingAvgCount = 50
        aveGenerality = 0
        aveGeneralityFreq = min(self.env.formatData.numTrainInstances,int(self.learningIterations/20)+1)

        if self.rebootFilename == None:
            self.timer = Timer()
            self.population = ClassifierSet()
        else:
            self.rebootPopulation()

        while self.explorIter < self.learningIterations:
            #Get New Instance and Run a learning algorithm
            state_phenotype = self.env.getTrainInstance()

            self.runIteration(state_phenotype,self.explorIter)

            #Basic Evaluations of Algorithm
            self.timer.startTimeEvaluation()

            if self.explorIter%aveGeneralityFreq == aveGeneralityFreq-1:
                aveGenerality = self.population.getAveGenerality(self)

            if len(self.trackingAccuracy) != 0:
                accuracy = sum(self.trackingAccuracy)/len(self.trackingAccuracy)
            else:
                accuracy = 0

            self.timer.updateGlobalTime()
            self.record.addToTracking(self.explorIter,accuracy,aveGenerality,
                                      self.trackingObj.macroPopSize,self.trackingObj.microPopSize,
                                      self.trackingObj.matchSetSize,self.trackingObj.correctSetSize,
                                      self.trackingObj.avgIterAge, self.trackingObj.subsumptionCount,
                                      self.trackingObj.crossOverCount, self.trackingObj.mutationCount,
                                      self.trackingObj.coveringCount,self.trackingObj.deletionCount,
                                      self.timer.globalTime,self.timer.globalMatching,
                                      self.timer.globalDeletion,self.timer.globalSubsumption,
                                      self.timer.globalSelection,self.timer.globalEvaluation)
            self.timer.stopTimeEvaluation()

            #Increment Instance & Iteration
            self.explorIter+=1
            self.env.newInstance()
        self.saveFinalMetrics()
        self.hasTrained = True
        return self

    def runIteration(self,state_phenotype,exploreIter):
        #Reset tracking object counters
        self.trackingObj.resetAll()

        #Form [M]
        self.population.makeMatchSet(state_phenotype,exploreIter,self)

        if self.trackAccuracyWhileFit:
            #Make a Prediction
            self.timer.startTimeEvaluation()
            prediction = Prediction(self,self.population)
            phenotypePrediction = prediction.getDecision()

            if self.env.formatData.discretePhenotype:
                if phenotypePrediction == state_phenotype[1]:
                    if len(self.trackingAccuracy) == self.movingAvgCount:
                        del self.trackingAccuracy[0]
                    self.trackingAccuracy.append(1)
                else:
                    if len(self.trackingAccuracy) == self.movingAvgCount:
                        del self.trackingAccuracy[0]
                    self.trackingAccuracy.append(0)
            else:
                predictionError = math.fabs(phenotypePrediction-float(state_phenotype[1]))
                phenotypeRange = self.env.formatData.phenotypeList[1] - self.env.formatData.phenotypeList[0]
                accuracyEstimate = 1.0 - (predictionError / float(phenotypeRange))
                if len(self.trackingAccuracy) == self.movingAvgCount:
                    del self.trackingAccuracy[0]
                self.trackingAccuracy.append(accuracyEstimate)
            self.timer.stopTimeEvaluation()

        #Form [C]
        self.population.makeCorrectSet(self,state_phenotype[1])

        #Update Parameters
        self.population.updateSets(self,exploreIter)

        #Perform Subsumption
        if self.doCorrectSetSubsumption:
            self.timer.startTimeSubsumption()
            self.population.doCorrectSetSubsumption(self)
            self.timer.stopTimeSubsumption()

        #Perform GA
        self.population.runGA(self,exploreIter,state_phenotype[0],state_phenotype[1])

        #Run Deletion
        self.timer.startTimeDeletion()
        self.population.deletion(self,exploreIter)
        self.timer.stopTimeDeletion()

        self.trackingObj.macroPopSize = len(self.population.popSet)
        self.trackingObj.microPopSize = self.population.microPopSize
        self.trackingObj.matchSetSize = len(self.population.matchSet)
        self.trackingObj.correctSetSize = len(self.population.correctSet)
        self.trackingObj.avgIterAge = self.population.getInitStampAverage()

        #Clear [M] and [C]
        self.population.clearSets()

    ##*************** Population Reboot ****************
    def saveFinalMetrics(self):
        self.finalMetrics = [self.learningIterations,self.timer.globalTime, self.timer.globalMatching,
                             self.timer.globalDeletion, self.timer.globalSubsumption, self.timer.globalSelection,
                             self.timer.globalEvaluation,copy.deepcopy(self.population.popSet)]

    def pickleModel(self,filename=None):
        if self.hasTrained:
            if filename == None:
                filename = 'pickled'+str(int(time.time()))
            outfile = open(filename,'wb')
            pickle.dump(self.finalMetrics,outfile)
            outfile.close()
        else:
            raise Exception("There is model to pickle, as the eLCS model has not been trained")

    def rebootPopulation(self):
        # Sets popSet and microPopSize of self.population, as well as trackingMetrics,
        file = open(self.rebootFilename, 'rb')
        rawData = pickle.load(file)
        file.close()

        popSet = rawData[7]
        microPopSize = 0
        for rule in popSet:
            microPopSize += rule.numerosity
        set = ClassifierSet()
        set.popSet = popSet
        set.microPopSize = microPopSize
        self.population = set
        self.timer = Timer()
        self.timer.globalAdd = rawData[1]
        self.timer.globalMatching = rawData[2]
        self.timer.globalDeletion = rawData[3]
        self.timer.globalSubsumption = rawData[4]
        self.timer.globalGA = rawData[5]
        self.timer.globalEvaluation = rawData[6]
        self.learningIterations += rawData[0]
        self.explorIter += rawData[0]

    ##*************** Export and Evaluation ****************
    def predict_proba(self, X):
        """Scikit-learn required: Test Accuracy of eLCS
            Parameters
            X: array-like {n_samples, n_features} Test instances to classify. ALL INSTANCE ATTRIBUTES MUST BE NUMERIC

            Returns
            y: array-like {n_samples} Classifications.
        """
        try:
            for instance in X:
                for value in instance:
                    if not (np.isnan(value)):
                        float(value)
        except:
            raise Exception("X must be fully numeric")

        instances = X.shape[0]
        predList = []

        for inst in range(instances):
            state = X[inst]
            self.population.makeEvalMatchSet(state, self)
            prediction = Prediction(self, self.population)
            probs = prediction.getProbabilities()
            predList.append(probs)
            self.population.clearSets()
        return np.array(predList)

    def predict(self, X):
        """Scikit-learn required: Test Accuracy of eLCS
            Parameters
            X: array-like {n_samples, n_features} Test instances to classify. ALL INSTANCE ATTRIBUTES MUST BE NUMERIC

            Returns
            y: array-like {n_samples} Classifications.
        """
        try:
            for instance in X:
                for value in instance:
                    if not (np.isnan(value)):
                        float(value)
        except:
            raise Exception("X must be fully numeric")

        instances = X.shape[0]
        predList = []

        for inst in range(instances):
            state = X[inst]
            self.population.makeEvalMatchSet(state, self)
            prediction = Prediction(self, self.population)
            phenotypeSelection = prediction.getDecision()
            predList.append(phenotypeSelection)
            self.population.clearSets()
        return np.array(predList)

    #Comment out score function if continuous phenotype is built in, so that RegressorMixin and ClassifierMixin default methods can be used appropriately
    def score(self,X,y):
        predList = self.predict(X)
        return balanced_accuracy_score(y, predList) #Make it balanced accuracy

    def exportIterationTrackingData(self,filename='iterationData.csv'):
        if self.hasTrained:
            self.record.exportTrackingToCSV(filename)
        else:
            raise Exception("There is no tracking data to export, as the eLCS model has not been trained")

    def exportFinalRulePopulation(self,headerNames=np.array([]),className="phenotype",filename='populationData.csv',DCAL=True):
        if self.hasTrained:
            if DCAL:
                self.record.exportPopDCAL(self,headerNames,className,filename)
            else:
                self.record.exportPop(self, headerNames, className, filename)
        else:
            raise Exception("There is no rule population to export, as the eLCS model has not been trained")

    def getFinalAccuracy(self):
        if self.hasTrained:
            originalTrainingData = self.env.formatData.savedRawTrainingData
            return self.score(originalTrainingData[0], originalTrainingData[1])
        else:
            raise Exception("There is no final training accuracy to return, as the XCS model has not been trained")

    def getFinalInstanceCoverage(self):
        if self.hasTrained:
            numCovered = 0
            originalTrainingData = self.env.formatData.savedRawTrainingData
            for state in originalTrainingData[0]:
                self.population.makeEvalMatchSet(state, self)
                predictionArray = Prediction(self, self.population)
                if predictionArray.hasMatch:
                    numCovered += 1
                self.population.clearSets()
            return numCovered/len(originalTrainingData[0])
        else:
            raise Exception("There is no final instance coverage to return, as the eLCS model has not been trained")

    def getFinalAttributeSpecificityList(self):
        if self.hasTrained:
            return self.population.getAttributeSpecificityList(self)
        else:
            raise Exception(
                "There is no final attribute specificity list to return, as the eLCS model has not been trained")

    def getFinalAttributeAccuracyList(self):
        if self.hasTrained:
            return self.population.getAttributeAccuracyList(self)
        else:
            raise Exception("There is no final attribute accuracy list to return, as the eLCS model has not been trained")

    #######################################################PRINT METHODS FOR DEBUGGING################################################################################

    def printClassifier(self,classifier):
        attributeCounter = 0

        for attribute in range(self.env.formatData.numAttributes):
            if attribute in classifier.specifiedAttList:
                specifiedLocation = classifier.specifiedAttList.index(attribute)
                if self.env.formatData.attributeInfoType[attributeCounter] == 0:  # isDiscrete
                    print(classifier.condition[specifiedLocation], end="\t\t\t\t")
                else:
                    print("[", end="")
                    print(
                        round(classifier.condition[specifiedLocation][0] * 10) / 10,
                        end=", ")
                    print(
                        round(classifier.condition[specifiedLocation][1] * 10) / 10,
                        end="")
                    print("]", end="\t\t")
            else:
                print("#", end="\t\t\t\t")
            attributeCounter += 1
        if self.env.formatData.discretePhenotype:
            print(classifier.phenotype,end="\t\t\t\t")
        else:
            print("[", end="")
            print(round(classifier.phenotype[0] * 10) / 10, end=", ")
            print(round(classifier.phenotype[1] * 10) / 10, end="")
            print("]",end="\t\t")
        if round(classifier.fitness*1000)/1000 != classifier.fitness:
            print(round(classifier.fitness*1000)/1000,end="\t\t")
        else:
            print(round(classifier.fitness * 1000) / 1000, end="\t\t\t")

        if round(classifier.accuracy * 1000) / 1000 != classifier.accuracy:
            print(round(classifier.accuracy*1000)/1000,end="\t\t")
        else:
            print(round(classifier.accuracy * 1000) / 1000, end="\t\t\t")
        print(classifier.numerosity)

    def printMatchSet(self):
        print("Match Set Size: "+str(len(self.population.matchSet)))
        for classifierRef in self.population.matchSet:
            self.printClassifier(self.population.popSet[classifierRef])
        print()

    def printCorrectSet(self):
        print("Correct Set Size: " + str(len(self.population.correctSet)))
        for classifierRef in self.population.correctSet:
            self.printClassifier(self.population.popSet[classifierRef])
        print()

    def printPopSet(self):
        print("Population Set Size: " + str(len(self.population.popSet)))
        for classifier in self.population.popSet:
            self.printClassifier(classifier)
        print()

    #######################################################TEMPORARY STORAGE OBJECTS################################################################################
class tempTrackingObj():
    #Tracks stats of every iteration (except accuracy, avg generality, and times)
    def __init__(self):
        self.macroPopSize = 0
        self.microPopSize = 0
        self.matchSetSize = 0
        self.correctSetSize = 0
        self.avgIterAge = 0
        self.subsumptionCount = 0
        self.crossOverCount = 0
        self.mutationCount = 0
        self.coveringCount = 0
        self.deletionCount = 0

    def resetAll(self):
        self.macroPopSize = 0
        self.microPopSize = 0
        self.matchSetSize = 0
        self.correctSetSize = 0
        self.avgIterAge = 0
        self.subsumptionCount = 0
        self.crossOverCount = 0
        self.mutationCount = 0
        self.coveringCount = 0
        self.deletionCount = 0
