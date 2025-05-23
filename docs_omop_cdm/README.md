# Modelo do banco de dados para o aplicativo SAÚDE! baseado no OMOP CDM

## 1 Introdução

### 1.1 Termos recorrentes

### 1.2 Versões utilizadas

### 1.3 FAQ

## 2 Descrição do OMOP CDM

### 2.1 Tabelas disponíveis

#### 2.1.1 Standardized clinical data

#### 2.1.2 Standardized health system

#### 2.1.1 Standardized vocabularies

#### 2.1.4 Standardized health economics

#### 2.1.5 Standardized derived elements

#### 2.1.6 Standardized metadata

## 3 Vocabulários

## 4 Modelo SAÚDE!

### 4.1 Diagrama do modelo

As tabelas estão divididas em grupos distintos:

-**app_saude** são as tabelas aderidas ao OMOP CDM e utilizadas para armazenar dados dentro do prontuário (menos RecurrenceRule)

As outras tabelas estão relacionadas aos mecanismos de funcionamento do aplicativo e não no "prontuário" aderido ao OMOP CDM.

-**auth** dados relacionados a autenticação

-**authtoken**

-**account**

-**socialaccount**

-**contenttypes**

-**admin**

-**sessions**

-**sites**

![Ideias geradas Guilherme](https://github.com/datasci4citizens/server-saude/tree/main/docs_omop_cdm/images/SAUDE-DB.png)

### 4.2 Explicação das tabelas e vocabulários escolhidos

## 5 Ferramentas importantes

### 5.1 ATHENA

### 5.2 THEMIS

### 5.3 ATLAS
