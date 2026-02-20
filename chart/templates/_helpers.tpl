{{/*
Expand the name of the chart.
*/}}
{{- define "jupyterlab-claude.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "jupyterlab-claude.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "jupyterlab-claude.labels" -}}
helm.sh/chart: {{ include "jupyterlab-claude.name" . }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "jupyterlab-claude.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "jupyterlab-claude.selectorLabels" -}}
app.kubernetes.io/name: {{ include "jupyterlab-claude.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
