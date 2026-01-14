package com.kirusa;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.Insets;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.prefs.Preferences;

import javax.swing.BorderFactory;
import javax.swing.JButton;
import javax.swing.JCheckBoxMenuItem;
import javax.swing.JDialog;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JMenu;
import javax.swing.JMenuBar;
import javax.swing.JMenuItem;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSplitPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;

import com.fasterxml.jackson.databind.ObjectMapper;

public class ChatClient extends JFrame {

    private JTextArea chatArea;
    private JTextArea debugLog;
    private JTextField inputField;
    private JTextField idField;
    private JButton sendButton;
    private JPanel statusLight;
    private JSplitPane splitPane;
    private JScrollPane debugScrollPane;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(java.time.Duration.ofSeconds(5))
            .build();

    private final Preferences prefs = Preferences.userNodeForPackage(ChatClient.class);
    private final String URL_KEY = "agent_base_url";
    private final String ID_KEY = "last_session_id";

    private String agentBaseUrl;
    private final DateTimeFormatter timeFormatter = DateTimeFormatter.ofPattern("HH:mm:ss");

    public ChatClient() {
        // Load Settings
        agentBaseUrl = prefs.get(URL_KEY, "http://localhost:8000");
        String savedId = prefs.get(ID_KEY, "default-id");

        setTitle("AI Agent Client");
        setSize(700, 800);
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        // --- 1. Menu Bar ---
        JMenuBar menuBar = new JMenuBar();
        JMenu configMenu = new JMenu("Config");

        JMenuItem clearItem = new JMenuItem("Clear Windows");
        clearItem.addActionListener(e -> clearWindows());

        JCheckBoxMenuItem toggleDebug = new JCheckBoxMenuItem("Show Debug Log", true);
        toggleDebug.addActionListener(e -> toggleDebugWindow(toggleDebug.isSelected()));

        JMenuItem settingsItem = new JMenuItem("Settings...");
        settingsItem.addActionListener(e -> showSettingsDialog());

        configMenu.add(toggleDebug);
        configMenu.add(settingsItem);
        configMenu.addSeparator(); // Adds a small line for organization
        configMenu.add(clearItem);
        menuBar.add(configMenu);
        setJMenuBar(menuBar);

        // --- 2. Top Control Panel ---
        JPanel controlPanel = new JPanel(new GridBagLayout());
        controlPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);

        // Row 0: ID and Status
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.weightx = 0;
        controlPanel.add(new JLabel("Session ID:"), gbc);

        idField = new JTextField(savedId, 15);
        gbc.gridx = 1;
        gbc.gridy = 0;
        gbc.weightx = 1.0;
        controlPanel.add(idField, gbc);

        JPanel statusPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        statusPanel.add(new JLabel("Status:"));
        statusLight = new JPanel() {
            @Override
            protected void paintComponent(Graphics g) {
                super.paintComponent(g);
                g.setColor(getBackground());
                g.fillOval(0, 0, 12, 12);
            }
        };
        statusLight.setPreferredSize(new Dimension(12, 12));
        statusLight.setBackground(Color.GRAY);
        statusPanel.add(statusLight);
        gbc.gridx = 2;
        gbc.gridy = 0;
        gbc.weightx = 0;
        controlPanel.add(statusPanel, gbc);

        // Row 1: Message and Send
        gbc.gridx = 0;
        gbc.gridy = 1;
        gbc.weightx = 0;
        controlPanel.add(new JLabel("Message:"), gbc);

        inputField = new JTextField();
        gbc.gridx = 1;
        gbc.gridy = 1;
        gbc.weightx = 1.0;
        controlPanel.add(inputField, gbc);

        sendButton = new JButton("Send");
        gbc.gridx = 2;
        gbc.gridy = 1;
        gbc.weightx = 0;
        controlPanel.add(sendButton, gbc);

        add(controlPanel, BorderLayout.NORTH);

        // --- 3. Center Area (Chat + Debug) ---
        chatArea = new JTextArea();
        chatArea.setEditable(false);
        chatArea.setLineWrap(true);
        chatArea.setWrapStyleWord(true);
        chatArea.setMargin(new Insets(10, 10, 10, 10));

        debugLog = new JTextArea();
        debugLog.setEditable(false);
        debugLog.setFont(new Font("Monospaced", Font.PLAIN, 12));
        debugLog.setForeground(new Color(0, 100, 0));
        debugScrollPane = new JScrollPane(debugLog);

        splitPane = new JSplitPane(JSplitPane.VERTICAL_SPLIT,
                new JScrollPane(chatArea), debugScrollPane);
        splitPane.setDividerLocation(400);
        add(splitPane, BorderLayout.CENTER);

        // Events
        sendButton.addActionListener(e -> sendMessage());
        inputField.addActionListener(e -> sendMessage());

        checkStatus();
    }

    private void clearWindows() {
        // Wipe the text areas
        chatArea.setText("");
        debugLog.setText("");

        // Optional: Log a fresh start so you know it was cleared manually
        logDebug("SYSTEM: Windows cleared by user.");
    }

    private void sendMessage() {
        String text = inputField.getText().trim();
        String idValue = idField.getText().trim();
        if (text.isEmpty()) {
            return;
        }

        prefs.put(ID_KEY, idValue);
        appendMessage("YOU: " + text);
        inputField.setText("");
        setLoading(true);

        String jsonPayload = String.format("{\"id\": \"%s\", \"message\": \"%s\"}", idValue, text);
        String fullUrl = agentBaseUrl.endsWith("/") ? agentBaseUrl + "generate" : agentBaseUrl + "/generate";

        logDebug("HTTP REQUEST [POST]\nURL: " + fullUrl + "\nPAYLOAD: " + jsonPayload);

        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(fullUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
                    .build();

            httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(response -> {
                        updateStatusLight(Color.GREEN);
                        String body = response.body();
                        logDebug("HTTP RESPONSE [Code " + response.statusCode() + "]\nBODY: " + body);

                        try {
                            // 1. Parse the entire response as a JSON Tree
                            com.fasterxml.jackson.databind.JsonNode rootNode = objectMapper.readTree(body);

                            // 2. Look for the "result" field specifically
                            if (rootNode.has("result")) {
                                return rootNode.get("result").asText();
                            }

                            return body; // Fallback
                        } catch (Exception e) {
                            return body;
                        }
                    })
                    .thenAccept(parsedText -> {
                        SwingUtilities.invokeLater(() -> {
                            // This parsedText now contains actual char(10) newlines
                            appendMessage("AGENT: " + parsedText);
                            appendSeparator();
                            setLoading(false);
                        });
                    })
                    .exceptionally(ex -> {
                        updateStatusLight(Color.RED);
                        handleError("Request Failed: " + ex.getMessage());
                        return null;
                    });
        } catch (Exception e) {
            handleError("Invalid URL: " + fullUrl);
        }
    }

    private void appendMessage(String msg) {
        chatArea.append(msg + "\n");
        // Auto Scroll Chat
        chatArea.setCaretPosition(chatArea.getDocument().getLength());
    }

    private void appendSeparator() {
        // Demarcation line after each interaction
        chatArea.append("__________________________________________________________________\n\n");
        chatArea.setCaretPosition(chatArea.getDocument().getLength());
    }

    private void logDebug(String content) {
        String timestamp = LocalTime.now().format(timeFormatter);
        SwingUtilities.invokeLater(() -> {
            debugLog.append("[" + timestamp + "] " + content + "\n---\n");
            // Auto Scroll Debug
            debugLog.setCaretPosition(debugLog.getDocument().getLength());
        });
    }

    private void toggleDebugWindow(boolean show) {
        if (show) {
            splitPane.setBottomComponent(debugScrollPane);
            splitPane.setDividerLocation(400);
            splitPane.setDividerSize(5);
        } else {
            splitPane.setBottomComponent(null);
            splitPane.setDividerSize(0);
        }
        splitPane.revalidate();
        splitPane.repaint();
    }

    private void showSettingsDialog() {
        JDialog dialog = new JDialog(this, "Configuration", true);
        dialog.setLayout(new BorderLayout(10, 10));

        // URL Input Panel
        JPanel panel = new JPanel(new GridLayout(2, 1, 5, 5));
        panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        JTextField urlInput = new JTextField(agentBaseUrl);
        panel.add(new JLabel("AI Agent Base URL:"));
        panel.add(urlInput);

        // Button Panel for Save and Info
        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));

        // NEW: LLM Info Button
        JButton infoButton = new JButton("Get LLM Info");
        infoButton.addActionListener(e -> {
            // Temporarily use the input text in case they haven't saved yet
            String tempUrl = urlInput.getText().trim();
            fetchLlmInfo(tempUrl);
        });

        JButton saveButton = new JButton("Save & Test");
        saveButton.addActionListener(e -> {
            agentBaseUrl = urlInput.getText().trim();
            prefs.put(URL_KEY, agentBaseUrl);
            logDebug("CONFIG: URL updated. Testing Health...");
            checkStatus();
            dialog.dispose();
        });

        buttonPanel.add(infoButton);
        buttonPanel.add(saveButton);

        dialog.add(panel, BorderLayout.CENTER);
        dialog.add(buttonPanel, BorderLayout.SOUTH);
        dialog.pack();
        dialog.setLocationRelativeTo(this);
        dialog.setVisible(true);
    }

    private void fetchLlmInfo(String baseUrl) {
        try {
            String infoUrl = baseUrl.endsWith("/") ? baseUrl + "llm-info" : baseUrl + "/llm-info";
            logDebug("GET LLM INFO: Fetching from " + infoUrl);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(infoUrl))
                    .header("accept", "application/json")
                    .GET()
                    .build();

            httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenAccept(response -> {
                        if (response.statusCode() == 200) {
                            logDebug("LLM INFO RECEIVED:\n" + response.body());
                        } else {
                            logDebug("LLM INFO FAILED: HTTP " + response.statusCode());
                        }
                    })
                    .exceptionally(ex -> {
                        logDebug("LLM INFO ERROR: " + ex.getMessage());
                        return null;
                    });
        } catch (Exception e) {
            logDebug("LLM INFO ERROR: Invalid URL construction.");
        }
    }

    private void checkStatus() {
        try {
            String healthUrl = agentBaseUrl.endsWith("/") ? agentBaseUrl + "health" : agentBaseUrl + "/health";
            HttpRequest request = HttpRequest.newBuilder().uri(URI.create(healthUrl)).GET().build();
            httpClient.sendAsync(request, HttpResponse.BodyHandlers.discarding())
                    .thenAccept(res -> updateStatusLight(res.statusCode() == 200 ? Color.GREEN : Color.RED))
                    .exceptionally(ex -> {
                        updateStatusLight(Color.RED);
                        return null;
                    });
        } catch (Exception e) {
            updateStatusLight(Color.RED);
        }
    }

    private void setLoading(boolean loading) {
        SwingUtilities.invokeLater(() -> {
            sendButton.setEnabled(!loading);
            inputField.setEditable(!loading);
            idField.setEditable(!loading);
        });
    }

    private void handleError(String errorMsg) {
        SwingUtilities.invokeLater(() -> {
            logDebug("ERROR: " + errorMsg);
            appendMessage("SYSTEM: Error occurred. Check debug log.");
            appendSeparator();
            setLoading(false);
        });
    }

    private void updateStatusLight(Color color) {
        SwingUtilities.invokeLater(() -> {
            statusLight.setBackground(color);
            statusLight.repaint();
        });
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            ChatClient client = new ChatClient();
            client.setLocationRelativeTo(null);
            client.setVisible(true);
        });
    }
}
