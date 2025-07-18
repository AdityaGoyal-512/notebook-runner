"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Play, CheckCircle, XCircle } from "lucide-react"

interface NotebookResult {
  success: boolean
  output: string
  error?: string
}

export default function NotebookRunner() {
  const [notebook1Result, setNotebook1Result] = useState<NotebookResult | null>(null)
  const [notebook2Result, setNotebook2Result] = useState<NotebookResult | null>(null)
  const [loading1, setLoading1] = useState(false)
  const [loading2, setLoading2] = useState(false)

  const runNotebook = async (notebookNumber: 1 | 2) => {
    const setLoading = notebookNumber === 1 ? setLoading1 : setLoading2
    const setResult = notebookNumber === 1 ? setNotebook1Result : setNotebook2Result

    setLoading(true)
    setResult(null)

    try {
      const response = await fetch(`/api/run-notebook-${notebookNumber}`, {
        method: "POST",
      })

      const result = await response.json()
      setResult(result)
    } catch (error) {
      setResult({
        success: false,
        output: "",
        error: "Failed to execute notebook",
      })
    } finally {
      setLoading(false)
    }
  }

  const renderOutput = (result: NotebookResult | null, loading: boolean) => {
    if (loading) {
      return (
        <div className="flex items-center justify-center p-8 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          Executing notebook...
        </div>
      )
    }

    if (!result) return null

    return (
      <div className="mt-4">
        <div className={`flex items-center mb-2 ${result.success ? "text-green-600" : "text-red-600"}`}>
          {result.success ? <CheckCircle className="h-5 w-5 mr-2" /> : <XCircle className="h-5 w-5 mr-2" />}
          <span className="font-medium">
            {result.success ? "Execution completed successfully" : "Execution failed"}
          </span>
        </div>
        <Card>
          <CardContent className="p-4">
            <pre className="whitespace-pre-wrap text-sm font-mono bg-gray-50 p-3 rounded border overflow-x-auto">
              {result.error || result.output || "No output"}
            </pre>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Notebook Runner</h1>
          <p className="text-lg text-gray-600">Execute Python notebooks and view their output in real-time</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Notebook 1 */}
          <Card className="shadow-lg">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Data Analysis Notebook</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                onClick={() => runNotebook(1)}
                disabled={loading1}
                size="lg"
                className="w-full h-16 text-lg font-semibold"
              >
                {loading1 ? <Loader2 className="h-6 w-6 animate-spin mr-2" /> : <Play className="h-6 w-6 mr-2" />}
                Run Notebook 1
              </Button>
              {renderOutput(notebook1Result, loading1)}
            </CardContent>
          </Card>

          {/* Notebook 2 */}
          <Card className="shadow-lg">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Machine Learning Notebook</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                onClick={() => runNotebook(2)}
                disabled={loading2}
                size="lg"
                className="w-full h-16 text-lg font-semibold"
                variant="secondary"
              >
                {loading2 ? <Loader2 className="h-6 w-6 animate-spin mr-2" /> : <Play className="h-6 w-6 mr-2" />}
                Run Notebook 2
              </Button>
              {renderOutput(notebook2Result, loading2)}
            </CardContent>
          </Card>
        </div>

        <div className="mt-12 text-center">
          <Card className="bg-white/50 backdrop-blur">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold mb-2">How it works</h3>
              <p className="text-gray-600">
                Click either button to execute the corresponding Python notebook on the server. The output will be
                displayed below each button in real-time.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
