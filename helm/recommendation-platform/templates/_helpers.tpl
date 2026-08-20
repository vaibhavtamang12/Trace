{{- define "recommendation-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- define "recommendation-platform.fullname" -}}
{{- if .Values.fullnameOverride }}{{ .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}{{- else }}{{ include "recommendation-platform.name" . }}{{- end }}
{{- end }}
{{- define "recommendation-platform.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "recommendation-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
{{- define "recommendation-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "recommendation-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
